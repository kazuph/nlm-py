# NLM Authentication Flow (Pyppeteer Implementation)

This document outlines the proposed flow for retrieving authentication tokens and cookies from NotebookLM using Pyppeteer, replacing the previous Go binary implementation.

## Overall Flow

```mermaid
graph TD
    subgraph get_auth
        direction LR
        ga_start[Start] --> ga_loop[Get Event Loop];
        ga_loop --> ga_run[asyncio.run(_get_auth_with_pyppeteer)];
        ga_run --> ga_result[Get Result];
        ga_result --> ga_end[End];
    end

    subgraph _get_auth_with_pyppeteer (Async)
        direction TB
        a1[Create Temp Dir] --> a2[Get Profile Path];
        a2 --> a3[Copy Profile Data];
        a3 --> a4[Launch Pyppeteer (userDataDir)];
        a4 --> a5[Navigate (NotebookLM)];
        a5 --> a6[Wait for WIZ_global_data];
        a6 --> a7[Extract Token/Cookies];
        a7 --> a8[Close Browser];
        a8 --> a9[Return Result];

        a3 -.-> subgraph CopyProfileData
            direction LR
            cp1[Define File List] --> cp2{File Exists?};
            cp2 -- Yes --> cp3[shutil.copy2];
            cp2 -- No --> cp4[Skip];
            cp3 & cp4 --> cp5{Loop Done?};
            cp5 -- No --> cp2;
            cp5 -- Yes --> cp6[Write Local State];
            cp6 --> cp7[Copy Done];
        end

        a6 & a7 -.-> subgraph ExtractAuth
            direction TB
            ex1[waitForFunction] --> ex2[evaluate (Token)];
            ex1 --> ex3[page.cookies()];
            ex3 --> ex4[_format_cookies];
            ex2 & ex4 --> ex5[Extraction Done];
        end

        a9 --> ga_result;
    end

    ga_start --> a1;

    %% Error Handling (Simplified)
    a1 -- Error --> err_cleanup[Cleanup Temp Dir];
    a3 -- Error --> err_cleanup;
    a4 -- Error --> err_cleanup;
    a5 -- Error --> err_browser_close[Close Browser];
    a6 -- Error --> err_browser_close;
    a7 -- Error --> err_browser_close;
    err_browser_close --> a8;
    a8 -- Error --> err_cleanup;
    err_cleanup --> ga_end;
```

## Key Steps

1.  **`get_auth` (Synchronous Wrapper):**
    *   Gets the current event loop.
    *   Runs the asynchronous `_get_auth_with_pyppeteer` function.
    *   Returns the result.
2.  **`_get_auth_with_pyppeteer` (Asynchronous Core):**
    *   Creates a temporary directory.
    *   Determines the path to the user's Chrome profile directory based on the OS.
    *   Copies essential files (`Cookies`, `Login Data`, `Web Data`) from the specified Chrome profile to the temporary directory. Creates a minimal `Local State` file.
    *   Launches Pyppeteer using the temporary directory as `userDataDir`.
    *   Navigates to `https://notebooklm.google.com`.
    *   Waits for the `WIZ_global_data` JavaScript object to become available (indicating successful login and page load).
    *   Extracts the authentication token (`WIZ_global_data.SNlM0e`) and relevant cookies using `page.evaluate()` and `page.cookies()`.
    *   Formats the cookies into a single string.
    *   Closes the browser.
    *   Returns the token and cookie string.
3.  **Helper Functions:**
    *   `_get_chrome_profile_path()`: Returns the OS-specific path to the Chrome user data directory.
    *   `_format_cookies()`: Formats the list of cookie dictionaries from Pyppeteer into a semicolon-separated string.