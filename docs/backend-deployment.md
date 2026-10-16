# Backend Deployment

Carbon Law backend can run locally or on a free host such as Render.

## Local
cd backend
uvicorn app:app --reload

## Free host
Use render.yaml for a free Render web service.

## Clio Grow integration
Clio Grow can be used as canonical intake and contact source. Parse webhook payloads into matters through POST /matters or a future /integrations/clio-webhook endpoint.
