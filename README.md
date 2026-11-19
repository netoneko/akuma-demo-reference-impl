# Akuma ecosystem demo reference services

A small reference implementation and shared contract for agents collaborating on the Akuma ecosystem demo. A Scala task board lets agents exchange progress and messages; a Rust Git Smart HTTP service accepts each agent's code so the host can clone and review it; a Python suite exercises both over the network. The authoritative agent-facing contract is [spec/SPEC.md](spec/SPEC.md). It replaces the older arithmetic-service contract in the archived demo brief for this exercise.

- `task-board/`: Scala task board, in-memory state.
- `git-server/`: Rust wrapper around the pinned `gitserver` crates, with on-disk bare repositories.
- `tests/`: Python standard-library remote acceptance tests.
- `spec/`: service and API contract to hand to agents.

These are reference services for a trusted demo network, not production services: there is no authentication or TLS, any participant can modify tasks or push to repositories, and board state is lost on restart. The Git repository data persists. The VM images, provisioning and launch orchestration are maintained separately.

## Run locally on Linux

Install JDK 17+, [Scala CLI](https://scala-cli.virtuslab.org/install/), Rust/Cargo, Python 3 and Git. The first builds need access to Maven, crates.io and the pinned Git dependency; cache dependencies in advance for offline use.

In separate terminals, from the repository root:

```sh
scala-cli run task-board/Main.scala --server=false
```

```sh
mkdir -p git-server/repos
for name in rust scala python; do git init --bare --initial-branch=main "git-server/repos/$name.git"; done
GIT_ROOT=git-server/repos cargo run --locked --manifest-path git-server/Cargo.toml
```

Create repositories before starting the Git service: it discovers them at startup. `PORT` overrides the respective service's port; `GIT_ROOT` selects its repository directory. The board defaults to 8082 and Git to 8081. For a fresh demo, stop the services and use a new Git directory; restarting the board clears tasks.

Run against disposable services (the tests create tasks and push commits to **all three** named repositories):

```sh
python3 tests/test_remote.py --board-url http://127.0.0.1:8082 --git-url http://127.0.0.1:8081
```

For a remote run, replace both addresses with the actual reachable URLs. An agent can publish an existing commit with `git push http://HOST:8081/rust.git HEAD:main` (choose its assigned repository). After an agent has pushed, review its work with `git clone http://HOST:8081/rust.git` (or `scala.git` / `python.git`) and inspect its log. The integration tests add commits to `main` in all three repositories; use only disposable repositories. Agents should push their deliverable to `main`.

## Example board requests

```sh
curl -s http://localhost:8082/health
curl -s -X POST http://localhost:8082/tasks -H 'Content-Type: application/json' -d '{"title":"Implement service","assignee":"agent-b"}'
curl -s -X POST http://localhost:8082/tasks/1/messages -H 'Content-Type: application/json' -d '{"author":"agent-b","text":"Started"}'
curl -s -X PATCH http://localhost:8082/tasks/1 -H 'Content-Type: application/json' -d '{"status":"done"}'
curl -s http://localhost:8082/tasks
```

See the [API contract](spec/SPEC.md) for validation rules, error codes, and repository provisioning. Local Linux checks do not demonstrate guest networking or image readiness.
