## Project Overview

This project, `social-auto-upload`, is a powerful automation tool designed to help content creators and operators efficiently publish video content to multiple domestic and international mainstream social media platforms in one click. The project implements video upload, scheduled release and other functions for platforms such as `Douyin`, `Bilibili`, `Xiaohongshu`, `Kuaishou`, `WeChat Channel`, `Baijiahao` and `TikTok`.

**Backend:**

*   Framework: Flask
*   Core Functionality:
    *   Handles file uploads and management.
    *   Interacts with a SQLite database to store information about files and user accounts.
    *   Uses `playwright` for browser automation to interact with social media platforms.
    *   Provides a RESTful API.
    *   Uses Server-Sent Events (SSE) for real-time communication during the login process.

**Command-line Interface:**

The project also provides a command-line interface (CLI) for users who prefer to work from the terminal. The CLI supports two main actions:

*   `login`: To log in to a social media platform.
*   `upload`: To upload a video to a social media platform, with an option to schedule the upload.

## Building and Running

### Backend

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Playwright browser drivers:**
    ```bash
    playwright install chromium
    ```

3.  **Initialize the database:**
    ```bash
    python db/createTable.py
    ```

4.  **Run the backend server:**
    ```bash
    python sau_backend.py
    ```
    The backend server will start on `http://localhost:5409`.

### Command-line Interface

To use the CLI, you can run the `cli_main.py` script with the appropriate arguments.

**Login:**

```bash
python cli_main.py <platform> <account_name> login
```

**Upload:**

```bash
python cli_main.py <platform> <account_name> upload <video_file> [-pt {0,1}] [-t YYYY-MM-DD HH:MM]
```

## Development Conventions

*   The backend code is located in the root directory and the `myUtils` and `uploader` directories.
*   The project uses a SQLite database for data storage. The database file is located at `db/database.db`.
*   The `conf.example.py` file should be copied to `conf.py` and configured with the appropriate settings.
*   The `requirements.txt` file lists the Python dependencies.
