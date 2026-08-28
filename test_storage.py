from app.services.storage import delete_file, download_file, upload_file

if __name__ == "__main__":
    key = "test/hello.txt"
    content = b"Hello from Hermes R2 test!"

    upload_file(key, content)
    print(f"Uploaded '{key}'.")

    downloaded = download_file(key)
    print(f"Downloaded content matches: {downloaded == content}")

    delete_file(key)
    print(f"Deleted '{key}'.")

    try:
        download_file(key)
        print("ERROR: file still exists after delete!")
    except Exception as exc:
        print(f"Confirmed deleted (expected error on re-fetch): {type(exc).__name__}")
