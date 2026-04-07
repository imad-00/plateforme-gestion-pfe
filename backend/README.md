# Backend - PFE Management Platform

Ce backend couvre Sprint 0, Sprint 1 et Sprint 2 (sans scope Sprint 3).

## Stack
- Django 5.x + DRF
- PostgreSQL
- Redis + Celery
- MinIO (S3)
- drf-spectacular
- pytest + pytest-django
- Docker Compose

## Environment Variables
Le projet charge la configuration depuis:
1. `backend/.env` (prioritaire)
2. les variables d'environnement du systeme

Exemple de configuration: `backend/.env.example`.

## Quick Start
1. Copier l'environnement local:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Lancer les services:
   ```bash
   docker compose up --build
   ```
3. Appliquer les migrations:
   ```bash
   docker compose exec web python manage.py migrate
   ```
4. Lancer les tests:
   ```bash
   docker compose exec web pytest
   ```

## Useful URLs
- API docs (Swagger): http://localhost:8000/api/docs/
- OpenAPI schema: http://localhost:8000/api/schema/
- Healthcheck: http://localhost:8000/api/health/
- Django Admin UI: http://localhost:8000/admin/

## Demo Admin Setup
1. Creer un superuser Django:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```
2. Se connecter via `/admin/`.
3. Verifier les modeles utiles pour la demo:
   - `User`
   - `StudentProfile`
   - `TeacherProfile`
   - `AcademicYear`

## Scope Reminder
Ce repository reste volontairement focalise sur:
- Sprint 0: fondation technique
- Sprint 1: auth & identite
- Sprint 2: annee academique + gestion admin minimale des comptes

Aucune logique de Sprint 3 (campagnes, sujets, groupes, affectation) n'est incluse ici.
