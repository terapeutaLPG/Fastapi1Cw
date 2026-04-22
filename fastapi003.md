# FastAPI — Frontend bez frameworka

> **Laboratorium 1.3** · Python · HTML · fetch API · URLSearchParams
>
> Wprawdzie opisywałem jako zaawansowane, ale dodam jeszcze osobny plik z tymi zaawansowanymi zagadnieniami. A tak najpierw jeszcze wykorzystywanie backendu się przyda
>
> *Jak połączyć FastAPI z HTML/JS — sześć wzorców, które wystarczą do zbudowania ciekawej aplikacji*

---

```
// ROZDZIAŁ 01

Serwowanie plików statycznych
StaticFiles — FastAPI jako pełny serwer aplikacji

────────────────────────────────────────
```

# Pliki statyczne w FastAPI

Do tej pory API zwracało wyłącznie JSON. Żeby serwować HTML, CSS i JavaScript z tego samego serwera, potrzebujemy `StaticFiles` — wbudowanego mechanizmu FastAPI.

```bash
pip install "fastapi[standard]" aiofiles
```

```
biblioteka/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── routers/
│   └── books.py
└── static/
    ├── index.html      ← jedyna strona aplikacji
    ├── style.css
    └── app.js
```

```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import books

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Biblioteka API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)

# StaticFiles musi być zarejestrowane jako ostatnie
# path="/" — wszystkie żądania, które nie pasują do routerów, trafiają tu
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

> **⚠️ Kolejność montowania**
>
> `app.mount()` ze `StaticFiles` zawsze umieszczaj **po** `include_router()`. FastAPI dopasowuje ścieżki w kolejności rejestracji — jeśli zamienisz kolejność, serwer nigdy nie dotrze do routerów API.

## Baza projektu — model i endpointy

Przez całe laboratorium będziemy pracować na tym samym projekcie. Zanim przejdziemy do frontendu, potrzebujemy działającego backendu.

```python
# models.py
from sqlalchemy import Column, Integer, String, Boolean, Float
from database import Base

class Book(Base):
    __tablename__ = "books"

    id        = Column(Integer, primary_key=True, index=True)
    title     = Column(String(200), nullable=False)
    author    = Column(String(100), nullable=False)
    year      = Column(Integer,     nullable=False)
    genre     = Column(String(50),  default="Unknown")
    rating    = Column(Float,       default=0.0)
    available = Column(Boolean,     default=True)
```

```python
# schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class BookCreate(BaseModel):
    title:  str   = Field(..., min_length=1, max_length=200)
    author: str   = Field(..., min_length=2, max_length=100)
    year:   int   = Field(..., ge=1000, le=2100)
    genre:  Optional[str]   = "Unknown"
    rating: Optional[float] = Field(default=0.0, ge=0.0, le=10.0)

class BookUpdate(BaseModel):
    title:     Optional[str]   = None
    author:    Optional[str]   = None
    year:      Optional[int]   = None
    genre:     Optional[str]   = None
    rating:    Optional[float] = None
    available: Optional[bool]  = None

class BookOut(BaseModel):
    id:        int
    title:     str
    author:    str
    year:      int
    genre:     str
    rating:    float
    available: bool

    model_config = {"from_attributes": True}
```

```python
# routers/books.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import Book
from schemas import BookCreate, BookUpdate, BookOut

router = APIRouter(prefix="/books", tags=["books"])

@router.post("/", response_model=BookOut, status_code=201)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    new_book = Book(**book.model_dump())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

@router.get("/", response_model=list[BookOut])
def list_books(
    author:    Optional[str]  = Query(None),
    genre:     Optional[str]  = Query(None),
    available: Optional[bool] = Query(None),
    search:    Optional[str]  = Query(None),
    page:      int            = Query(1, ge=1),
    limit:     int            = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Book)
    if author:
        q = q.filter(Book.author.ilike(f"%{author}%"))
    if genre:
        q = q.filter(Book.genre.ilike(f"%{genre}%"))
    if available is not None:
        q = q.filter(Book.available == available)
    if search:
        pattern = f"%{search}%"
        q = q.filter(Book.title.ilike(pattern) | Book.author.ilike(pattern))
    return q.offset((page - 1) * limit).limit(limit).all()

@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(404, f"Książka #{book_id} nie istnieje")
    return book

@router.patch("/{book_id}", response_model=BookOut)
def update_book(book_id: int, data: BookUpdate, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Nie znaleziono książki")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return book

@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Nie znaleziono książki")
    db.delete(book)
    db.commit()
```

Uruchom serwer i sprawdź w Swagger UI czy wszystkie endpointy działają, zanim przejdziesz do frontendu.

```bash
uvicorn main:app --reload
# http://127.0.0.1:8000/docs
```

---

```
// ROZDZIAŁ 02

Wzorzec 1 — fetch POST z formularzem
Tworzenie zasobu bez przeładowania strony

────────────────────────────────────────
```

# Wzorzec 1 — POST z formularzem HTML

Najprostszy wzorzec: użytkownik wypełnia formularz, JavaScript przechwytuje `submit`, wysyła dane do API i pokazuje wynik — wszystko bez przeładowania strony.

```html
<!-- static/index.html -->
<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <title>Biblioteka</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>

<h1>📚 Dodaj książkę</h1>

<form id="addForm">
  <label>Tytuł
    <input type="text" id="title" required>
  </label>
  <label>Autor
    <input type="text" id="author" required>
  </label>
  <label>Rok
    <input type="number" id="year" min="1000" max="2100" required>
  </label>
  <label>Gatunek
    <input type="text" id="genre" placeholder="np. Fantasy">
  </label>
  <button type="submit">Dodaj</button>
</form>

<div id="feedback"></div>

<script>
  const form     = document.getElementById("addForm");
  const feedback = document.getElementById("feedback");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();  // blokuj domyślne przeładowanie strony

    // 1. Zbierz dane z formularza
    const body = {
      title:  document.getElementById("title").value.trim(),
      author: document.getElementById("author").value.trim(),
      year:   parseInt(document.getElementById("year").value),
      genre:  document.getElementById("genre").value.trim() || "Unknown",
    };

    // 2. Wyślij POST do API
    const res = await fetch("/books/", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });

    // 3. Obsłuż odpowiedź
    if (res.status === 201) {
      const book = await res.json();
      feedback.innerHTML = `<p class="ok">✅ Dodano: <strong>${book.title}</strong> (ID: ${book.id})</p>`;
      form.reset();
    } else {
      feedback.innerHTML = `<p class="err">❌ Błąd ${res.status}. Sprawdź dane.</p>`;
    }
  });
</script>

</body>
</html>
```

> **📋 Trzy obowiązkowe elementy każdego fetch POST**
>
> `method: "POST"` — domyślnie fetch używa GET.
>
> `headers: { "Content-Type": "application/json" }` — bez tego FastAPI zwróci 422, bo nie wie w jakim formacie są dane.
>
> `body: JSON.stringify(body)` — obiekt JS musi być zamieniony na string JSON przed wysłaniem.

Sprawdź działanie: otwórz `http://localhost:8000`, wypełnij formularz i kliknij Dodaj. W zakładce Network przeglądarki (F12) zobaczysz żądanie POST i odpowiedź 201.

---

```
// ROZDZIAŁ 03

Wzorzec 2 — dynamiczna lista z DELETE
Renderowanie danych i usuwanie elementów bez odświeżania

────────────────────────────────────────
```

# Wzorzec 2 — lista z DELETE

Drugi wzorzec to pobieranie listy danych przez `GET` i renderowanie jej w HTML przez JavaScript, z możliwością usunięcia każdego elementu kliknięciem przycisku.

```html
<!-- Dodaj do index.html, poniżej formularza -->

<hr>
<h2>Lista książek</h2>
<button id="refreshBtn">🔄 Odśwież</button>
<ul id="bookList"></ul>
```

```javascript
// Dodaj do <script> w index.html

// ── Pobieranie i renderowanie listy ───────────────────
async function loadBooks() {
  const res   = await fetch("/books/");
  const books = await res.json();

  const list = document.getElementById("bookList");

  if (books.length === 0) {
    list.innerHTML = "<li>Brak książek w bibliotece.</li>";
    return;
  }

  // Każdy element dostaje unikalny id="book-{id}" — przyda się przy usuwaniu
  list.innerHTML = books.map(b => `
    <li id="book-${b.id}">
      <strong>${b.title}</strong> — ${b.author} (${b.year})
      <span class="${b.available ? 'tag-ok' : 'tag-err'}">
        ${b.available ? "dostępna" : "wypożyczona"}
      </span>
      <button onclick="deleteBook(${b.id})">🗑 Usuń</button>
    </li>
  `).join("");
}

// ── Usuwanie elementu ─────────────────────────────────
async function deleteBook(id) {
  if (!confirm(`Usunąć książkę #${id}?`)) return;

  const res = await fetch(`/books/${id}`, { method: "DELETE" });

  if (res.status === 204) {
    // Usuń element z DOM — bez ponownego zapytania do API
    document.getElementById(`book-${id}`).remove();
  } else if (res.status === 404) {
    alert("Książka nie istnieje — odświeżam listę.");
    loadBooks();
  } else {
    alert(`Błąd ${res.status}`);
  }
}

document.getElementById("refreshBtn").addEventListener("click", loadBooks);
loadBooks();  // załaduj listę od razu przy otwarciu strony
```

> **🔗 Dlaczego** `res.status === 204`**, nie** `res.ok`**?**
>
> `DELETE` zwraca 204 No Content — odpowiedź bez body. `res.ok` jest `true` dla wszystkich kodów 2xx (200, 201, 204...), więc technicznie też zadziałałoby. Ale sprawdzanie konkretnego kodu jest czytelniejsze i pozwala osobno obsłużyć 200 vs 204, jeśli tego potrzebujesz.
>
> Jedna ważna zasada: **nigdy nie próbuj wywołać** `res.json()` **gdy status to 204** — odpowiedź nie ma body i otrzymasz błąd parsowania.

## Optymalizacja — nie przeładowuj wszystkiego

Przy usunięciu elementu użyliśmy `document.getElementById(\`book-${id}\`).remove()`zamiast ponownego`loadBooks()`. To ważny wzorzec — nie odpytuj API ponownie, jeśli już wiesz co się zmieniło. Serwer potwierdził usunięcie kodem 204, więc można bezpiecznie usunąć element z drzewa DOM.

---

```
// ROZDZIAŁ 04

Wzorzec 3 — URLSearchParams i filtrowanie
Budowanie query string, filtrowanie po stronie backendu

────────────────────────────────────────
```

# Wzorzec 3 — filtrowanie i wyszukiwanie

Zamiast filtrować dane w JS po ich pobraniu (co pobiera za dużo), wysyłamy filtry jako query parametry do backendu i pobieramy już przefiltrowany wynik.

```html
<!-- Sekcja wyszukiwarki -->
<hr>
<h2>🔍 Szukaj</h2>

<div class="search-bar">
  <input type="text"   id="searchInput"  placeholder="Tytuł lub autor...">
  <input type="text"   id="genreInput"   placeholder="Gatunek">
  <select id="availSelect">
    <option value="">Wszystkie</option>
    <option value="true">Dostępne</option>
    <option value="false">Wypożyczone</option>
  </select>
  <button onclick="searchBooks()">Szukaj</button>
</div>

<div id="searchResults"></div>
```

```javascript
async function searchBooks() {
  // URLSearchParams buduje bezpieczny query string
  // Automatycznie enkoduje znaki specjalne (spacje, polskie litery itp.)
  const params = new URLSearchParams();

  const search    = document.getElementById("searchInput").value.trim();
  const genre     = document.getElementById("genreInput").value.trim();
  const available = document.getElementById("availSelect").value;

  // Dodaj parametr TYLKO gdy pole jest wypełnione
  if (search)    params.append("search",    search);
  if (genre)     params.append("genre",     genre);
  if (available) params.append("available", available);

  // Gotowy URL: /books/?search=Tolkien&available=true
  const url = `/books/?${params.toString()}`;
  const res = await fetch(url);
  const data = await res.json();

  const div = document.getElementById("searchResults");

  if (data.length === 0) {
    div.innerHTML = "<p>Brak wyników dla podanych kryteriów.</p>";
    return;
  }

  div.innerHTML = `
    <p>Znaleziono: <strong>${data.length}</strong></p>
    <table>
      <thead>
        <tr><th>Tytuł</th><th>Autor</th><th>Rok</th><th>Gatunek</th><th>Dostępna</th></tr>
      </thead>
      <tbody>
        ${data.map(b => `
          <tr>
            <td>${b.title}</td>
            <td>${b.author}</td>
            <td>${b.year}</td>
            <td>${b.genre}</td>
            <td>${b.available ? "✅" : "❌"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}
```

> **📋 Dlaczego URLSearchParams, nie sklejanie stringa?**
>
> Ręczne sklejanie: `` `/books/?search=${search}&genre=${genre}` `` — złamie się gdy `search` zawiera `&`, `=` lub polskie znaki.
>
> `URLSearchParams` enkoduje automatycznie: spacja → `%20`, `ą` → `%C4%85`, `&` w wartości → `%26`.
>
> Dodatkowa zaleta: puste parametry (gdy pole niepełnione) po prostu nie są dodawane — nie musisz sprawdzać if/else przy każdym polu.

## Wyszukiwanie w czasie rzeczywistym

Jeśli chcesz filtrować natychmiast podczas wpisywania, podepnij funkcję pod zdarzenie `input`:

```javascript
document.getElementById("searchInput").addEventListener("input", searchBooks);
```

Przy bardzo szybkim pisaniu warto użyć *debounce* — opóźnienia, żeby nie wysyłać zapytania po każdej literze:

```javascript
let debounceTimer;
document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(searchBooks, 300);  // czekaj 300ms po ostatnim naciśnięciu
});
```

---

```
// ROZDZIAŁ 05

Wzorzec 4 — paginacja
Stronicowanie wyników, przyciski Poprzednia / Następna

────────────────────────────────────────
```

# Wzorzec 4 — paginacja

Backend obsługuje parametry `page` i `limit`. Frontend musi zapamiętać bieżącą stronę i odpowiednio aktualizować przyciski.

```html
<hr>
<h2>📄 Wszystkie książki</h2>

<div id="pageContent"></div>

<div class="pagination">
  <button id="btnPrev" onclick="changePage(-1)" disabled>← Poprzednia</button>
  <span id="pageInfo"></span>
  <button id="btnNext" onclick="changePage(1)">Następna →</button>
</div>
```

```javascript
let currentPage = 1;
const PAGE_LIMIT = 5;  // książek na stronę

async function loadPage(page) {
  const res  = await fetch(`/books/?page=${page}&limit=${PAGE_LIMIT}`);
  const data = await res.json();

  const container = document.getElementById("pageContent");

  container.innerHTML = data.length
    ? data.map(b => `
        <div class="book-card">
          <strong>${b.title}</strong>
          <span>${b.author} · ${b.year}</span>
          <span class="genre">${b.genre}</span>
        </div>
      `).join("")
    : "<p>Brak wyników na tej stronie.</p>";

  // Zaktualizuj stan przycisków
  currentPage = page;
  document.getElementById("pageInfo").textContent  = `Strona ${page}`;
  document.getElementById("btnPrev").disabled = (page <= 1);
  // Jeśli dostaliśmy mniej niż PAGE_LIMIT rekordów, to jesteśmy na ostatniej stronie
  document.getElementById("btnNext").disabled = (data.length < PAGE_LIMIT);
}

function changePage(delta) {
  loadPage(currentPage + delta);
}

loadPage(1);
```

> **🔗 Jak backend oblicza offset**
>
> ```
> Strona 1: skip = (1-1) * 5 = 0   → rekordy  0–4
> Strona 2: skip = (2-1) * 5 = 5   → rekordy  5–9
> Strona 3: skip = (3-1) * 5 = 10  → rekordy 10–14
> ```
>
> Wzór: `skip = (page - 1) * limit`
>
> W SQLAlchemy: `.offset(skip).limit(limit)`

## Wyświetlanie całkowitej liczby wyników

Jeśli chcesz pokazać "Strona 2 z 7", backend musi zwrócić total count. Wymaga to zmiany endpointu:

```python
# routers/books.py — wersja z metadanymi paginacji
@router.get("/")
def list_books(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    q     = db.query(Book)
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "pages": (total + limit - 1) // limit,  # zaokrąglenie w górę
        "page":  page,
        "items": [BookOut.model_validate(b) for b in items],
    }
```

```javascript
// Zaktualizowany loadPage z totalem
async function loadPage(page) {
  const res  = await fetch(`/books/?page=${page}&limit=${PAGE_LIMIT}`);
  const data = await res.json();

  // data to teraz { total, pages, page, items }
  renderBooks(data.items);

  document.getElementById("pageInfo").textContent =
    `Strona ${data.page} z ${data.pages} (${data.total} wyników)`;
  document.getElementById("btnPrev").disabled = (data.page <= 1);
  document.getElementById("btnNext").disabled = (data.page >= data.pages);
}
```

> **⚠️ Zmiana response_model**
>
> Kiedy endpoint zwraca słownik z `items` zamiast bezpośrednio listy, usuń `response_model=list[BookOut]` z dekoratora lub zdefiniuj nowy schemat dla odpowiedzi z paginacją. Inaczej Pydantic będzie próbował dopasować słownik do listy i zwróci błąd 500.

---

```
// ROZDZIAŁ 06

Wzorzec 5 — formularz edycji in-place
Ładowanie aktualnych danych, wysyłanie PATCH

────────────────────────────────────────
```

# Wzorzec 5 — edycja in-place

Użytkownik klika "Edytuj" przy konkretnej książce, formularz wypełnia się jej aktualnymi danymi, po zapisaniu widać zaktualizowaną wersję.

```html
<!-- Panel edycji — ukryty domyślnie -->
<div id="editPanel" style="display:none;">
  <h3>✏️ Edytuj książkę</h3>
  <form id="editForm">
    <input type="hidden" id="editId">
    <label>Tytuł    <input type="text"   id="editTitle"></label>
    <label>Autor    <input type="text"   id="editAuthor"></label>
    <label>Rok      <input type="number" id="editYear"></label>
    <label>Gatunek  <input type="text"   id="editGenre"></label>
    <label>
      <input type="checkbox" id="editAvailable"> Dostępna
    </label>
    <div class="btn-row">
      <button type="submit">💾 Zapisz</button>
      <button type="button" onclick="closeEdit()">Anuluj</button>
    </div>
  </form>
</div>
```

```javascript
// ── Otwarcie panelu edycji ─────────────────────────────
async function openEdit(id) {
  // Pobierz aktualne dane książki z API
  const res = await fetch(`/books/${id}`);

  if (res.status === 404) {
    alert("Nie znaleziono książki.");
    return;
  }

  const book = await res.json();

  // Wypełnij pola aktualnymi wartościami
  document.getElementById("editId").value          = book.id;
  document.getElementById("editTitle").value       = book.title;
  document.getElementById("editAuthor").value      = book.author;
  document.getElementById("editYear").value        = book.year;
  document.getElementById("editGenre").value       = book.genre;
  document.getElementById("editAvailable").checked = book.available;

  document.getElementById("editPanel").style.display = "block";
  document.getElementById("editTitle").focus();  // ustaw kursor w pierwszym polu
}

function closeEdit() {
  document.getElementById("editPanel").style.display = "none";
  document.getElementById("editForm").reset();
}

// ── Wysyłanie PATCH ────────────────────────────────────
document.getElementById("editForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const id = document.getElementById("editId").value;

  // PATCH — wysyłamy TYLKO zmienione pola
  // Strategia: zbierz wszystkie pola, backend obsłuży exclude_none
  const body = {
    title:     document.getElementById("editTitle").value.trim()  || undefined,
    author:    document.getElementById("editAuthor").value.trim() || undefined,
    year:      parseInt(document.getElementById("editYear").value) || undefined,
    genre:     document.getElementById("editGenre").value.trim()  || undefined,
    available: document.getElementById("editAvailable").checked,
  };

  // Usuń klucze z wartością undefined przed serializacją
  const cleanBody = Object.fromEntries(
    Object.entries(body).filter(([, v]) => v !== undefined)
  );

  const res = await fetch(`/books/${id}`, {
    method:  "PATCH",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(cleanBody),
  });

  if (res.ok) {
    const updated = await res.json();
    // Zaktualizuj element w istniejącej liście bez pełnego przeładowania
    const li = document.getElementById(`book-${id}`);
    if (li) {
      li.querySelector("strong").textContent = updated.title;
      // ... zaktualizuj pozostałe pola elementu
    }
    closeEdit();
  } else {
    const err = await res.json();
    alert(`Błąd: ${err.detail}`);
  }
});
```

> **📋 PUT vs PATCH — kiedy używać czego**
>
> `PUT` — zastępuje **cały** zasób. Jeśli nie wyślesz jakiegoś pola, zostanie wymazane lub ustawi się wartość domyślna.
>
> `PATCH` — aktualizuje **wybrane** pola. Reszta zostaje bez zmian. Dlatego w Pydantic używamy `Optional` z `default=None` i `model_dump(exclude_none=True)`.
>
> Do formularza edycji profilu, ustawień, statusu — zawsze PATCH. PUT zostawiaj dla endpointów, gdzie klient świadomie zastępuje kompletny obiekt.

Dodaj przycisk "Edytuj" do elementów listy z poprzedniego rozdziału:

```javascript
// Zmień fragment renderowania listy w loadBooks():
list.innerHTML = books.map(b => `
  <li id="book-${b.id}">
    <strong>${b.title}</strong> — ${b.author} (${b.year})
    <button onclick="openEdit(${b.id})">✏️ Edytuj</button>
    <button onclick="deleteBook(${b.id})">🗑 Usuń</button>
  </li>
`).join("");
```

---

```
// ROZDZIAŁ 07

Wzorzec 6 — obsługa błędów HTTP
Reagowanie na kody statusu, komunikaty z backendu, walidacja klienta

────────────────────────────────────────
```

# Wzorzec 6 — obsługa błędów

Każde zapytanie do API może zakończyć się błędem. Profesjonalna aplikacja obsługuje je jawnie — zamiast milczeć albo wyświetlać techniczne komunikaty użytkownikowi.

## Dwie warstwy walidacji

```
Użytkownik klika "Wyślij"
        │
        ▼
┌─────────────────────┐
│  Walidacja klienta  │  ← natychmiastowa, bez sieci, lepsza UX
│  (JavaScript)       │
└────────┬────────────┘
         │ dane OK
         ▼
┌─────────────────────┐
│  FastAPI / Pydantic │  ← zawsze działa, nawet gdy ktoś pominie frontend
│  (serwer)           │
└─────────────────────┘
```

> **⚠️ Walidacja klienta to wygoda, nie bezpieczeństwo**
>
> Walidacja w JavaScript może być pominięta przez każdego — curl, Postman, zmodyfikowany formularz. Zawsze waliduj dane **też** po stronie backendu. Pydantic robi to za Ciebie automatycznie, zwracając 422 ze szczegółową listą błędów.

## Walidacja po stronie klienta

```javascript
function validateBook(data) {
  const errors = {};

  if (!data.title || data.title.length < 1)
    errors.title = "Tytuł jest wymagany.";

  if (!data.author || data.author.length < 2)
    errors.author = "Autor musi mieć co najmniej 2 znaki.";

  if (!data.year || data.year < 1000 || data.year > 2100)
    errors.year = "Rok musi być między 1000 a 2100.";

  return errors;
}

function showFieldErrors(errors) {
  // Wyczyść poprzednie błędy
  document.querySelectorAll(".field-error").forEach(el => el.textContent = "");
  document.querySelectorAll("input").forEach(el => el.classList.remove("invalid"));

  for (const [field, msg] of Object.entries(errors)) {
    const errEl = document.getElementById(`err-${field}`);
    const input = document.getElementById(field);
    if (errEl) errEl.textContent = msg;
    if (input) input.classList.add("invalid");
  }
}
```

```html
<!-- Formularz z miejscami na błędy per-pole -->
<form id="addForm">
  <label>Tytuł
    <input type="text" id="title">
    <span class="field-error" id="err-title"></span>
  </label>
  <label>Autor
    <input type="text" id="author">
    <span class="field-error" id="err-author"></span>
  </label>
  <label>Rok
    <input type="number" id="year">
    <span class="field-error" id="err-year"></span>
  </label>
  <button type="submit">Dodaj</button>
</form>
```

## Centralna obsługa kodów HTTP

```javascript
async function handleApiError(res) {
  switch (res.status) {
    case 400:
      return "Nieprawidłowe dane żądania.";

    case 401:
      return "Musisz być zalogowany.";

    case 403:
      return "Brak uprawnień do tej operacji.";

    case 404:
      return "Zasób nie istnieje.";

    case 409:
      return "Konflikt — taki zasób już istnieje.";

    case 422: {
      // FastAPI zwraca listę błędów walidacji — pokażmy je wszystkie
      const body = await res.json();
      const msgs = body.detail
        .map(e => `${e.loc.slice(1).join(".")}: ${e.msg}`)
        .join(" | ");
      return `Błąd walidacji: ${msgs}`;
    }

    case 429:
      return "Zbyt wiele żądań. Poczekaj chwilę i spróbuj ponownie.";

    case 500:
      return "Błąd serwera. Spróbuj za chwilę.";

    default:
      return `Nieoczekiwany błąd HTTP ${res.status}.`;
  }
}
```

## Obsługa błędów sieci

```javascript
// Kompletny przykład — formularz z pełną obsługą błędów
document.getElementById("addForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const data = {
    title:  document.getElementById("title").value.trim(),
    author: document.getElementById("author").value.trim(),
    year:   parseInt(document.getElementById("year").value),
  };

  // 1. Walidacja klienta
  const errors = validateBook(data);
  if (Object.keys(errors).length > 0) {
    showFieldErrors(errors);
    return;  // nie wysyłaj jeśli są błędy
  }

  // 2. Zapytanie do API
  let res;
  try {
    res = await fetch("/books/", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(data),
    });
  } catch (networkErr) {
    // fetch rzuca wyjątek tylko gdy serwer jest niedostępny (brak sieci, timeout)
    // Kody błędów HTTP (4xx, 5xx) NIE rzucają wyjątku — trafiają do normalnej gałęzi
    showMessage("❌ Nie można połączyć z serwerem. Sprawdź czy backend działa.", "err");
    return;
  }

  // 3. Obsługa odpowiedzi
  if (res.status === 201) {
    const book = await res.json();
    showMessage(`✅ Dodano: ${book.title}`, "ok");
    e.target.reset();
    loadBooks();
  } else {
    const msg = await handleApiError(res);
    showMessage(`❌ ${msg}`, "err");
  }
});

function showMessage(text, type) {
  const el = document.getElementById("feedback");
  el.textContent   = text;
  el.className     = type;
}
```

> **🔗 Kiedy fetch rzuca wyjątek?**
>
> `fetch` rzuca wyjątek `TypeError` **tylko** w przypadku problemów sieciowych: brak połączenia, timeout, zablokowany przez CORS, nieprawidłowy URL.
>
> Kody HTTP takie jak 400, 404, 500 **nie** rzucają wyjątku — `res.ok` jest wtedy `false`, ale musisz to sprawdzić sam. Pominięcie tego sprawdzenia to jeden z najczęstszych błędów przy nauce fetch API.

---

```
// ROZDZIAŁ 08

Kalkulator API
Mały projekt spinający wzorce 1 i 6

────────────────────────────────────────
```

# Mini-projekt: Kalkulator API

Prosty przykład pokazujący jak reagować na błędy logiki biznesowej (dzielenie przez zero) w odróżnieniu od błędów walidacji.

```python
# routers/calculator.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/calc", tags=["calculator"])

class CalcRequest(BaseModel):
    a: float
    b: float

@router.post("/add")
def add(req: CalcRequest):
    return {"result": req.a + req.b, "operation": f"{req.a} + {req.b}"}

@router.post("/subtract")
def subtract(req: CalcRequest):
    return {"result": req.a - req.b, "operation": f"{req.a} - {req.b}"}

@router.post("/multiply")
def multiply(req: CalcRequest):
    return {"result": req.a * req.b, "operation": f"{req.a} × {req.b}"}

@router.post("/divide")
def divide(req: CalcRequest):
    if req.b == 0:
        # 400 Bad Request — błąd logiki, nie walidacji danych
        raise HTTPException(status_code=400, detail="Nie można dzielić przez zero")
    return {"result": req.a / req.b, "operation": f"{req.a} ÷ {req.b}"}
```

```html
<!-- static/calc.html -->
<h1>🧮 Kalkulator</h1>

<div class="calc">
  <input type="number" id="numA" placeholder="Liczba A" step="any">
  <select id="operator">
    <option value="add">+</option>
    <option value="subtract">−</option>
    <option value="multiply">×</option>
    <option value="divide">÷</option>
  </select>
  <input type="number" id="numB" placeholder="Liczba B" step="any">
  <button onclick="calculate()">=</button>
</div>

<div id="calcResult"></div>

<script>
  async function calculate() {
    const a  = parseFloat(document.getElementById("numA").value);
    const b  = parseFloat(document.getElementById("numB").value);
    const op = document.getElementById("operator").value;
    const div = document.getElementById("calcResult");

    if (isNaN(a) || isNaN(b)) {
      div.innerHTML = `<span class="err">Wpisz dwie liczby.</span>`;
      return;
    }

    let res;
    try {
      res = await fetch(`/calc/${op}`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ a, b }),
      });
    } catch {
      div.innerHTML = `<span class="err">Brak połączenia z serwerem.</span>`;
      return;
    }

    const data = await res.json();

    if (res.ok) {
      // data.result to liczba, data.operation to ładny opis
      div.innerHTML = `
        <span class="ok">${data.operation} = <strong>${data.result}</strong></span>
      `;
    } else {
      // 400 — błąd logiki (np. dzielenie przez zero)
      div.innerHTML = `<span class="err">❌ ${data.detail}</span>`;
    }
  }
</script>
```

> **📋 400 vs 422 — różnica, którą warto zapamiętać**
>
> `422 Unprocessable Entity` — Pydantic odrzucił dane przed wejściem do funkcji. Typ się nie zgadza, wartość poza zakresem, brakujące pole.
>
> `400 Bad Request` — dane mają poprawny format, ale logika biznesowa je odrzuca. Dzielenie przez zero jest poprawną liczbą (walidacja przejdzie), ale nie ma sensu matematycznie.
>
> Używaj `HTTPException(400, ...)` do błędów logiki, nie próbuj udawać że to błąd walidacji.

---

```
// ROZDZIAŁ 09

Ćwiczenia
Zadania do samodzielnego wykonania

────────────────────────────────────────
```

# Ćwiczenia laboratoryjne

> **📌 Wskazówka**
>
> Każde ćwiczenie jest niezależne i rozbudowuje projekt Biblioteka z tego laboratorium. Zacznij od ćwiczenia 1, uruchom i przetestuj, zanim przejdziesz do kolejnego. Najczęstszy błąd to próba napisania wszystkiego naraz — wtedy trudno zlokalizować gdzie coś poszło nie tak.

## Ćwiczenie 1 — TODO z SQLite

Zbuduj API do zarządzania zadaniami z podstawowym frontendem.

1. Zdefiniuj model `Task` z polami: `id`, `title` (wymagany), `description`, `done` (bool, domyślnie False), `created_at` (datetime)
2. Stwórz pełny CRUD: `GET /tasks`, `POST /tasks`, `PATCH /tasks/{id}` (zmiana `done`), `DELETE /tasks/{id}`
3. W HTML: formularz dodawania zadania (Wzorzec 1) + lista z checkboxem "Oznacz jako done" i przyciskiem usuwania (Wzorzec 2)
4. Dodaj filtr `GET /tasks?done=false` i przycisk "Pokaż tylko nieukończone" w interfejsie (Wzorzec 3)

## Ćwiczenie 2 — Wyszukiwarka z paginacją

Rozbuduj interfejs Biblioteki o zaawansowane wyszukiwanie.

1. Połącz filtrowanie i paginację w jednym widoku — wyszukujesz, dostajesz wyniki podzielone na strony
2. Zapamiętaj aktywne filtry w zmiennych JS tak, żeby zmiana strony nie czyściła wyszukiwania
3. Wyświetl "Znaleziono X wyników" nad listą — wymaga `total` count z backendu
4. Dodaj przycisk "Wyczyść filtry" który resetuje wszystkie pola i przeładowuje pełną listę

## Ćwiczenie 3 — Kompletne CRUD w jednym widoku

Zintegruj wszystkie sześć wzorców w jednej aplikacji.

1. Lewa kolumna: formularz dodawania + sekcja wyszukiwania
2. Prawa kolumna: lista z paginacją, każdy element ma przyciski "Edytuj" i "Usuń"
3. Kliknięcie "Edytuj" otwiera panel edycji (Wzorzec 5) wypełniony aktualnymi danymi
4. Każda akcja (dodanie, edycja, usunięcie) wyświetla komunikat przez 3 sekundy, potem znika

```javascript
// Wskazówka do punktu 4 — automatyczne ukrywanie komunikatu
function showMessage(text, type, duration = 3000) {
  const el = document.getElementById("feedback");
  el.textContent = text;
  el.className   = type;
  setTimeout(() => { el.textContent = ""; el.className = ""; }, duration);
}
```

---

> **🏆 Mini-projekt — Aplikacja TODO z autoryzacją**
>
> Połącz wiedzę z Lab 1.2 (JWT, role) i Lab 1.3 (frontend), budując pełną aplikację:
>
> Backend: rejestracja i logowanie, każdy user ma własne zadania, admin widzi wszystkie.
>
> Frontend: strona logowania (POST do `/auth/token`, zapis tokenu w `sessionStorage`), po zalogowaniu — lista własnych zadań z pełnym CRUD.
>
> Kluczowy element: każdy fetch do chronionych endpointów musi wysyłać `Authorization: Bearer {token}` w nagłówku. Gdy token wygaśnie (401), przekieruj na stronę logowania.

---

```
// ROZDZIAŁ 10

Ściągawka
Wzorce, typowe błędy, przydatne snippety

────────────────────────────────────────
```

# Ściągawka — Lab 1.3

## Sześć wzorców fetch

| Wzorzec          | Metoda   | Kluczowy element                         | Kod odpowiedzi |
|------------------|----------|------------------------------------------|----------------|
| Formularz → POST | `POST`   | `JSON.stringify(body)` + Content-Type    | 201            |
| Lista + DELETE   | `DELETE` | `res.status === 204`, `.remove()` z DOM  | 204            |
| Filtrowanie      | `GET`    | `URLSearchParams`, puste pola pomiń      | 200            |
| Paginacja        | `GET`    | `?page=X&limit=Y`, `data.length < limit` | 200            |
| Edycja in-place  | `PATCH`  | Pobierz GET → wypełnij formularz → PATCH | 200            |
| Obsługa błędów   | dowolna  | `switch(res.status)`, catch dla sieci    | 4xx / 5xx      |

## Typowe błędy początkujących

| Błąd                                        | Skutek                        | Poprawka                                      |
|---------------------------------------------|-------------------------------|-----------------------------------------------|
| Brak `Content-Type: application/json`       | 422 z backendu                | Zawsze dodawaj nagłówek przy POST/PATCH       |
| `res.json()` przy statusie 204              | SyntaxError w konsoli         | Sprawdź status przed parsowaniem body         |
| Brak `e.preventDefault()`                   | Strona przeładowuje się       | Zawsze jako pierwsza linia handlera submit    |
| Filtrowanie danych w JS zamiast na serwerze | Pobierasz więcej niż potrzeba | Wysyłaj filtry jako query params              |
| `fetch` nie rzuca wyjątku przy 404/500      | Błąd ignorowany               | Sprawdzaj `res.ok` lub konkretny `res.status` |
| `parseInt()` na pustym stringu              | `NaN` wysyłane do API         | Waliduj dane przed `fetch`                    |

## Snippety gotowe do użycia

```javascript
// Bezpieczne pobieranie danych z obsługą błędów
async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    // 204 nie ma body
    if (res.status === 204) return null;
    return res.json();
  } catch (e) {
    if (e.name === "TypeError") throw new Error("Brak połączenia z serwerem.");
    throw e;
  }
}

// Użycie:
try {
  const book = await apiFetch("/books/", {
    method: "POST",
    body: JSON.stringify({ title: "Hobbit", author: "Tolkien", year: 1937 }),
  });
  console.log("Dodano:", book);
} catch (e) {
  console.error(e.message);  // czytelny komunikat błędu
}
```

```javascript
// Debounce dla wyszukiwania w czasie rzeczywistym
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

document.getElementById("searchInput")
  .addEventListener("input", debounce(searchBooks, 300));
```

```javascript
// Automatyczne ukrywanie komunikatu
function showMessage(text, type = "ok", ms = 3000) {
  const el = document.getElementById("feedback");
  el.textContent = text;
  el.className   = `message ${type}`;
  setTimeout(() => { el.textContent = ""; el.className = ""; }, ms);
}
```

## Kody statusów HTTP — skrót

| Kod | Nazwa                 | Kiedy zwracasz          |
|-----|-----------------------|-------------------------|
| 200 | OK                    | GET, PATCH — sukces     |
| 201 | Created               | POST — nowy zasób       |
| 204 | No Content            | DELETE — brak body      |
| 400 | Bad Request           | Błąd logiki biznesowej  |
| 404 | Not Found             | Zasób nie istnieje      |
| 409 | Conflict              | Duplikat (email, tytuł) |
| 422 | Unprocessable Entity  | Błąd walidacji Pydantic |
| 500 | Internal Server Error | Nieobsłużony wyjątek    |

## Przydatne komendy

```bash
# Start serwera z podglądem zmian
uvicorn main:app --reload

# Swagger UI z endpointami
open http://127.0.0.1:8000/docs

# Inspekcja bazy danych SQLite
sqlite3 biblioteka.db ".tables"
sqlite3 biblioteka.db "SELECT * FROM books LIMIT 5;"

# Testowy POST przez curl
curl -X POST http://localhost:8000/books/ \
  -H "Content-Type: application/json" \
  -d '{"title":"Hobbit","author":"Tolkien","year":1937}'
```

---

*Kolejne laboratorium (1.4 - w zasadzie 1.3a) — programowanie asynchroniczne z* `async`*/*`await`*, WebSocket dla funkcji real-time oraz konteneryzacja aplikacji w Docker.*

---

*FastAPI · fetch API · URLSearchParams · HTML/JS*