use gitserver_core::discovery::RepoStore;
use gitserver_http::{AuthConfig, ServicePolicy, SharedState, router};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let root = std::env::var("GIT_ROOT").unwrap_or_else(|_| "repos".into());
    let port = std::env::var("PORT").unwrap_or_else(|_| "8081".into());
    std::fs::create_dir_all(&root)?;
    let store = RepoStore::discover(root.into(), 1)?;
    let state = SharedState::with_store_and_auth_policy(
        store, AuthConfig::default(), ServicePolicy { receive_pack: true, ..Default::default() },
    );
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await?;
    println!("Git server listening on {}", listener.local_addr()?);
    axum::serve(listener, router(state)).await?;
    Ok(())
}
