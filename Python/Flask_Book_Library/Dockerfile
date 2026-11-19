# Używamy oficjalnego obrazu Pythona
FROM python:3.9-slim

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

ENV FLASK_ENV=development
ENV PASSWORD=1qaz@WSX

# Najpierw kopiujemy tylko listy zależności - dzięki temu warstwa z `pip install`
# jest cache'owana i nie przebudowuje się przy każdej zmianie kodu
COPY requirements.txt requirements-test.txt ./

# Instalujemy zależności aplikacji oraz testów
RUN pip install --no-cache-dir -r requirements.txt -r requirements-test.txt

# Kopiujemy pliki projektu do kontenera
COPY . .

# Uruchamiamy testy jednostkowe - jeśli którykolwiek test się nie powiedzie,
# pytest zwraca niezerowy kod wyjścia i `docker build` kończy się błędem
RUN python -m pytest

# Ustawiamy zmienną środowiskową, aby Flask wiedział, jak uruchomić aplikację
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose the port the app runs on
EXPOSE 5000

# Uruchamiamy aplikację
CMD ["flask", "run"]
