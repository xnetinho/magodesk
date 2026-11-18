fn main() {
    #[cfg(windows)]
    {
        use std::io::Write;
        let mut res = winres::WindowsResource::new();
        res.set_icon("../../res/icon.ico")
            .set_language(winapi::um::winnt::MAKELANGID(
                winapi::um::winnt::LANG_ENGLISH,
                winapi::um::winnt::SUBLANG_ENGLISH_US,
            ))
            .set_manifest_file("../../res/manifest.xml");
        // Rebranded builds: the self-extracting exe must not claim to be RustDesk.
        if let Some(name) = option_env!("RD_APP_NAME").filter(|n| !n.trim().is_empty()) {
            let name = name.trim();
            res.set("ProductName", name)
                .set("InternalName", name)
                .set("FileDescription", &format!("{name} Remote Desktop"))
                .set("OriginalFilename", &format!("{name}.exe"));
        }
        match res.compile() {
            Err(e) => {
                write!(std::io::stderr(), "{}", e).unwrap();
                std::process::exit(1);
            }
            Ok(_) => {}
        }
    }
}
