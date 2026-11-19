# Akuma demo services contract, version 1

This is the common contract for the reference implementation and the demo agents. It replaces the arithmetic service contract in the archived ecosystem demo brief for this exercise. URLs are supplied by the host; clients must not assume VM addresses. Both services listen on all interfaces. HTTP is unauthenticated and intended only for an isolated, trusted demo network.

## Task board (default port 8082)

All request and response bodies are UTF-8 JSON. Responses, including errors, have `Content-Type: application/json`. A task has this shape:

```json
{"id":1,"title":"Implement service","description":"Details","assignee":"agent-b","status":"open","messages":[{"author":"agent-b","text":"Started"}]}
```

IDs are positive integers allocated by the server. `title` is a non-blank string; `description` and `assignee` are strings (empty means unset). Status is `open`, `in_progress`, or `done`. Messages have non-blank string `author` and `text` fields, and retain insertion order. There are no timestamps or size guarantees. State is held in memory and disappears when the service restarts. Concurrent requests must not lose successful updates.

| Method and path | Request | Success |
| --- | --- | --- |
| GET /health | none | 200 `{"status":"ok"}` |
| GET /tasks | none | 200 JSON array of tasks, in creation order |
| POST /tasks | `title` required; `description`, `assignee` optional | 201 task, defaults `""`, `""`, `open`, empty messages |
| GET /tasks/{id} | none | 200 task |
| PATCH /tasks/{id} | nonempty object containing any of `title`, `description`, `assignee`, `status` | 200 updated task; unspecified fields unchanged |
| POST /tasks/{id}/messages | `author` and `text` required | 201 created message |

Invalid JSON, invalid or missing fields, unknown fields, or an empty patch return 400. Nonexistent or malformed IDs return 404. Unknown paths and unsupported methods return 404. Error bodies are JSON objects, with no required fields. Query strings have no effect. Operations do not delete tasks or messages.

## Git service (default port 8081)

The service provides Git Smart HTTP clone, fetch and push at `/<name>.git`. Repositories are bare and provisioned by the operator **before the server starts**, not created by clients. Names used by this demo are simple lowercase letters, digits and hyphens; the examples use `rust`, `scala`, and `python`. Provision each bare repository with `main` as its default branch (`git init --bare --initial-branch=main`). Each agent pushes its deliverable to `main`; the host can then clone it without choosing a branch. Each repository is independent and persists on disk across server restarts. Pushes to existing repositories and fetching the pushed commits must work using the ordinary Git CLI. The host must be able to clone each agent's repository and review its commits. `GET /healthz` returns 200 when ready. A missing repository must not accept pushes. No authentication, authorization, TLS, repository creation API, is provided; restrict network access to trusted demo participants. Provision a fresh repository directory for each demo run.

## Acceptance

Run `tests/test_remote.py` with the actual board and Git base URLs. Tests create tasks and push commits to the supplied pre-provisioned test repositories; use disposable instances. They require Python 3 and Git. The suite exits nonzero if any test fails. The contract is independent of guest networking and toolchain provisioning; this repository only verifies the services on Linux.
