use hbb_common::config::{self, Config, Socks5Server};
use std::collections::HashMap;

const HOST: Option<&str> = option_env!("RD_HOST");
const KEY: Option<&str> = option_env!("RD_KEY");
const APP_NAME: Option<&str> = option_env!("RD_APP_NAME");

fn non_empty(v: Option<&'static str>) -> Option<&'static str> {
    v.map(str::trim).filter(|s| !s.is_empty())
}

/// Server (host, public key) baked in at compile time; `None` for a stock build.
pub fn server() -> Option<(&'static str, &'static str)> {
    Some((non_empty(HOST)?, non_empty(KEY)?))
}

pub fn is_captive() -> bool {
    server().is_some()
}

/// Product name baked in at compile time; `None` keeps the stock "RustDesk".
fn app_name() -> Option<&'static str> {
    non_empty(APP_NAME)
}

/// The name decides the IPC pipe, the config directory and the service name,
/// so it must be set before anything reads a `Config`.
fn set_app_name(name: &str) {
    *config::APP_NAME.write().unwrap() = name.to_owned();
}

/// The WebSocket scheme (`wss`) is picked from `api-server` starting with `https`,
/// so it has to be https even though no API is ever called (register-device=N).
fn api_url(host: &str) -> String {
    // shortcut: an IPv6 literal would be cut at its first colon, and it cannot hold a TLS cert anyway
    format!("https://{}", host.split(':').next().unwrap_or(host))
}

fn locked_options(host: &str, key: &str) -> HashMap<String, String> {
    let mut m = HashMap::new();
    m.insert("custom-rendezvous-server".to_owned(), host.to_owned());
    m.insert("key".to_owned(), key.to_owned());
    // empty, so a stale relay saved by the user cannot take over; hbbs hands out the relay
    m.insert("relay-server".to_owned(), String::new());
    m.insert("api-server".to_owned(), api_url(host));
    m.insert("enable-check-update".to_owned(), "N".to_owned());
    m.insert("allow-auto-update".to_owned(), "N".to_owned());
    m
}

/// Proxy and network settings stay visible: companies behind a proxy need to type theirs.
fn builtin_options() -> HashMap<String, String> {
    let mut m: HashMap<String, String> = [
        "hide-server-settings",
        "hide-websocket-settings",
        // is_custom_client() turns true with a new name and would show a "powered by" link
        "hide-powered-by-me",
    ]
        .iter()
        .map(|k| (k.to_string(), "Y".to_owned()))
        .collect();
    // the open-source server has no API on :21114, so never try to reach one
    m.insert("register-device".to_owned(), "N".to_owned());
    m
}

/// WebSocket (relay only, no P2P) is used exactly when a proxy is set; everyone else keeps P2P.
fn websocket_value(has_proxy: bool) -> &'static str {
    if has_proxy {
        "Y"
    } else {
        "N"
    }
}

fn sync_websocket_for(has_proxy: bool) {
    config::OVERWRITE_SETTINGS.write().unwrap().insert(
        "allow-websocket".to_owned(),
        websocket_value(has_proxy).to_owned(),
    );
}

pub fn sync_websocket() {
    if is_captive() {
        sync_websocket_for(Config::get_socks().is_some());
    }
}

/// Use instead of `Config::set_socks` so the WebSocket switch follows the proxy.
pub fn set_socks(socks: Option<Socks5Server>) {
    Config::set_socks(socks);
    sync_websocket();
}

/// Server, key and update options override anything the user saved, and the
/// settings pages that would edit them are hidden.
pub fn apply() {
    let Some((host, key)) = server() else {
        return;
    };
    if let Some(name) = app_name() {
        set_app_name(name);
    }
    let locked = locked_options(host, key);
    config::OVERWRITE_SETTINGS.write().unwrap().extend(locked.clone());
    // enable-check-update is read from the local config, the rest from the server one
    config::OVERWRITE_LOCAL_SETTINGS.write().unwrap().extend(locked);
    config::BUILTIN_SETTINGS.write().unwrap().extend(builtin_options());
    sync_websocket();
}

/// `id@other-server` would send the session to a server the owner does not run.
pub fn peer_id(id: &str) -> &str {
    if is_captive() {
        id.split('@').next().unwrap_or(id)
    } else {
        id
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const HOST_T: &str = "rustdesk.example.com";
    const KEY_T: &str = "KEY=";

    #[test]
    fn stock_build_is_not_captive() {
        assert!(non_empty(None).is_none());
        assert!(non_empty(Some("  ")).is_none());
        assert_eq!(non_empty(Some(" a.b ")), Some("a.b"));
    }

    #[test]
    fn locks_server_key_and_updates() {
        let m = locked_options(HOST_T, KEY_T);
        assert_eq!(m["custom-rendezvous-server"], HOST_T);
        assert_eq!(m["key"], KEY_T);
        assert_eq!(m["relay-server"], "");
        assert_eq!(m["enable-check-update"], "N");
        assert_eq!(m["allow-auto-update"], "N");
    }

    #[test]
    fn api_url_comes_from_the_host_and_drops_the_port() {
        assert_eq!(api_url(HOST_T), "https://rustdesk.example.com");
        assert_eq!(api_url("rustdesk.example.com:21116"), "https://rustdesk.example.com");
        assert_eq!(locked_options(HOST_T, KEY_T)["api-server"], "https://rustdesk.example.com");
    }

    #[test]
    fn hides_server_but_keeps_proxy_settings_visible() {
        let m = builtin_options();
        assert_eq!(m["hide-server-settings"], "Y");
        assert_eq!(m["hide-websocket-settings"], "Y");
        assert_eq!(m["register-device"], "N");
        assert!(!m.contains_key("hide-proxy-settings"));
        assert!(!m.contains_key("hide-network-settings"));
    }

    #[test]
    fn hides_powered_by_link() {
        assert_eq!(builtin_options()["hide-powered-by-me"], "Y");
    }

    #[test]
    fn app_name_is_empty_when_unset() {
        assert_eq!(non_empty(None), None);
        assert_eq!(non_empty(Some(" MagoDesk ")), Some("MagoDesk"));
    }

    #[test]
    fn app_name_moves_the_ipc_pipe_away_from_rustdesk() {
        set_app_name("MagoDesk");
        assert!(Config::ipc_path("").contains("MagoDesk"));
        assert!(!Config::ipc_path("").contains("RustDesk"));
        assert_eq!(config::APP_NAME.read().unwrap().as_str(), "MagoDesk");
    }

    #[test]
    fn websocket_follows_proxy() {
        assert_eq!(websocket_value(true), "Y");
        assert_eq!(websocket_value(false), "N");
    }

    // one test: these touch the same process-wide settings
    #[test]
    fn locked_settings_win_and_pick_wss_through_the_proxy() {
        config::OVERWRITE_SETTINGS
            .write()
            .unwrap()
            .extend(locked_options(HOST_T, KEY_T));
        assert_eq!(Config::get_option("custom-rendezvous-server"), HOST_T);
        Config::set_option("custom-rendezvous-server".into(), "evil.example".into());
        assert_eq!(Config::get_option("custom-rendezvous-server"), HOST_T);
        Config::set_option("key".into(), "OTHER=".into());
        assert_eq!(Config::get_option("key"), KEY_T);

        sync_websocket_for(false);
        assert!(!config::use_ws());
        assert_eq!(
            hbb_common::websocket::check_ws("rustdesk.example.com:21116"),
            "rustdesk.example.com:21116"
        );

        sync_websocket_for(true);
        assert!(config::use_ws());
        assert_eq!(
            hbb_common::websocket::check_ws("rustdesk.example.com:21116"),
            "wss://rustdesk.example.com/ws/id"
        );
        assert_eq!(
            hbb_common::websocket::check_ws("rustdesk.example.com:21117"),
            "wss://rustdesk.example.com/ws/relay"
        );

        Config::set_option("allow-websocket".into(), "N".into());
        assert!(config::use_ws(), "user cannot turn WebSocket off behind a proxy");
    }
}
