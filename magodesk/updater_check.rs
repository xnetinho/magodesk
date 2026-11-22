//! Update check against OUR releases instead of api.rustdesk.com.
//!
//! GitHub answers `GET https://github.com/<owner>/<repo>/releases/latest` with a 302 to the page of the newest stable
//! (non pre-release) release: `.../releases/tag/vX.Y.Z`. The HTTP client follows it, and the final URL of the response is
//! exactly what the stock update code expects, so nothing else has to change: it then downloads and verifies
//! `rustdesk-update.json` and its signature. No API, no token and no rate limit are involved.
//!
//! The repository comes from `RD_UPDATE_REPO` at build time (the workflow passes `github.repository`). A build without
//! the captive server keeps the stock values, so upstream's own unit tests still describe the code they test.

const REPO: Option<&str> = option_env!("RD_UPDATE_REPO");
const DEFAULT_REPO: &str = "xnetinho/magodesk";
const STOCK_REPO: &str = "rustdesk/rustdesk";

/// `owner/repo` that publishes the releases and signs their metadata.
pub fn update_repo() -> &'static str {
    if !crate::captive::is_captive() {
        return STOCK_REPO;
    }
    REPO.map(str::trim).filter(|r| r.split_once('/').is_some()).unwrap_or(DEFAULT_REPO)
}

pub fn update_owner_repo() -> (&'static str, &'static str) {
    update_repo().split_once('/').unwrap_or(("rustdesk", "rustdesk"))
}

fn release_page_prefix() -> String {
    format!("https://github.com/{}/releases/tag/", update_repo())
}

/// Only the Windows build that is INSTALLED updates itself (the daily loop starts only for an installed service; the
/// portable exe cannot, because the updater refuses a build that is not installed). macOS has no Developer ID and
/// Android has no in-app installer.
pub fn auto_update_enabled() -> bool {
    cfg!(target_os = "windows")
}

/// Android only shows a notice with the link of the release; it never downloads or installs anything.
pub fn update_notice_enabled() -> bool {
    cfg!(target_os = "android")
}

/// Whether the update check runs at all in this build.
pub fn check_enabled() -> bool {
    auto_update_enabled() || update_notice_enabled()
}

/// The final URL of the answer, if it is exactly a tag page of our repository. Anything else (another host, a query, a
/// fragment, a nested path) is refused, so a hijacked redirect cannot send the updater elsewhere.
pub fn release_page_from_final_url(url: &str) -> Option<String> {
    let prefix = release_page_prefix();
    let tag = url.strip_prefix(prefix.as_str())?;
    if tag.is_empty() || tag.contains(['/', '?', '#', '%', '\\', ' ', '"']) || tag == "." || tag == ".." {
        return None;
    }
    Some(url.to_owned())
}

/// JSON body the stock code parses (`VersionCheckResponse`). The address was validated by `release_page_from_final_url`,
/// which refuses quotes and backslashes, so no escaping is needed.
pub fn response_body(release_page: &str) -> Vec<u8> {
    format!("{{\"url\":\"{release_page}\"}}").into_bytes()
}

/// Replaces the request of `do_check_software_update` (rules.py): same HTTP client and TLS handling, but a plain GET to
/// our releases/latest, and the stock `process_software_update_check_response` gets the JSON it expects.
pub async fn check_latest_release() -> hbb_common::ResultType<hbb_common::bytes::Bytes> {
    use hbb_common::{
        bail,
        tls::{get_cached_tls_type, upsert_tls_cache, TlsType},
    };
    let url = format!("https://github.com/{}/releases/latest", update_repo());
    let proxy_conf = hbb_common::config::Config::get_socks();
    let tls_url = crate::hbbs_http::get_url_for_tls(&url, &proxy_conf);
    let tls_type = get_cached_tls_type(tls_url);
    let is_tls_not_cached = tls_type.is_none();
    let tls_type = tls_type.unwrap_or(TlsType::Rustls);
    let client = crate::hbbs_http::create_http_client_async(tls_type, false);
    let (used_tls_type, response) = match client.get(&url).send().await {
        Ok(resp) => (tls_type, resp),
        Err(err) if is_tls_not_cached && err.is_request() => {
            let tls_type = TlsType::NativeTls;
            let client = crate::hbbs_http::create_http_client_async(tls_type, false);
            (tls_type, client.get(&url).send().await?)
        }
        Err(err) => return Err(err.into()),
    };
    upsert_tls_cache(tls_url, used_tls_type, false);
    if !response.status().is_success() {
        bail!("Update check failed with HTTP status: {}", response.status());
    }
    match release_page_from_final_url(response.url().as_str()) {
        Some(page) => Ok(hbb_common::bytes::Bytes::from(response_body(&page))),
        None => bail!("Update check ended on an unexpected URL: {}", response.url()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Without RD_HOST/RD_KEY the build is not captive, so these tests see the stock repository. The URL logic is the
    // same for any repository: the prefix is the only thing that differs.
    fn page(tag: &str) -> String {
        format!("{}{tag}", release_page_prefix())
    }

    #[test]
    fn accepts_the_tag_page_of_the_update_repository() {
        let want = page("v1.0.1");
        assert_eq!(release_page_from_final_url(&want).as_deref(), Some(want.as_str()));
    }

    #[test]
    fn refuses_anything_that_is_not_exactly_the_tag_page() {
        let p = release_page_prefix();
        let owner_repo = update_repo();
        for bad in [
            String::new(),
            "/".into(),
            "https://github.com/someone/else/releases/tag/v1.0.1".into(),
            format!("https://evil.example/{owner_repo}/releases/tag/v1.0.1"),
            format!("http://github.com/{owner_repo}/releases/tag/v1.0.1"),
            p.clone(),
            format!("{p}v1.0.1/extra"),
            format!("{p}v1.0.1?x=1"),
            format!("{p}v1.0.1#a"),
            format!("{p}v1%2F0"),
            format!("{p}.."),
            format!("https://github.com/{owner_repo}/releases/download/v1.0.1/a.exe"),
            format!("/{owner_repo}/releases/tag/v1.0.1"),
        ] {
            assert_eq!(release_page_from_final_url(&bad), None, "{bad}");
        }
    }

    #[test]
    fn the_body_is_the_json_the_stock_code_expects() {
        assert_eq!(response_body("https://x/y"), br#"{"url":"https://x/y"}"#);
    }

    #[test]
    fn a_quote_in_the_tag_is_refused_so_the_body_cannot_break_out_of_the_json() {
        assert_eq!(release_page_from_final_url(&page("v1\"},{\"x")), None);
    }

    #[test]
    fn owner_and_repo_are_one_pair_and_the_check_is_per_platform() {
        let (o, r) = update_owner_repo();
        assert_eq!(format!("{o}/{r}"), update_repo());
        assert_eq!(check_enabled(), cfg!(any(target_os = "windows", target_os = "android")));
        assert!(!(auto_update_enabled() && update_notice_enabled()));
    }
}
