package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/chromedp/cdproto/network"
	"github.com/chromedp/chromedp"
)

// AuthResult は認証情報の出力形式
type AuthResult struct {
	AuthToken string `json:"auth_token"`
	Cookies   string `json:"cookies"`
}

var (
	debug       bool
	profileName string
	outputFile  string
	envFile     bool
)

func init() {
	flag.BoolVar(&debug, "debug", false, "Enable debug output")
	flag.StringVar(&outputFile, "output", "", "Output file path (default: stdout)")
	flag.BoolVar(&envFile, "env", true, "Save auth info to .nlm/env file")
}

func main() {
	log.SetPrefix("nlm-auth: ")
	log.SetFlags(0)

	flag.Parse()

	// コマンドライン引数からプロファイル名を取得
	args := flag.Args()
	if len(args) > 0 {
		profileName = args[0]
	} else {
		// 環境変数から取得するか、デフォルト値を使用
		profileName = getEnvOrDefault("NLM_BROWSER_PROFILE", "Default")
	}

	fmt.Println("🔐 NotebookLM 認証情報の抽出を開始します")
	fmt.Printf("📂 Chromeプロファイル: %s を使用します\n", profileName)
	fmt.Println("🌐 Google アカウントにログイン済みであることを確認してください")
	if debug {
		fmt.Println("🐛 デバッグモードが有効です - ブラウザウィンドウが表示されます")
	}

	// 認証情報を取得
	token, cookies, err := getAuth(profileName)
	if err != nil {
		fmt.Println("❌ 認証情報の抽出に失敗しました")
		fmt.Println("🔍 Chrome で Google アカウントにログインしていることを確認してください")
		fmt.Fprintf(os.Stderr, "エラー: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("✅ 認証情報の抽出に成功しました")

	// 結果をJSON形式で出力
	result := AuthResult{
		AuthToken: token,
		Cookies:   cookies,
	}

	// 環境変数ファイルに保存
	if envFile {
		if err := saveToEnvFile(token, cookies, profileName); err != nil {
			fmt.Printf("⚠️ 環境変数ファイルへの保存に失敗しました: %v\n", err)
		} else {
			homeDir, _ := os.UserHomeDir()
			envFilePath := filepath.Join(homeDir, ".nlm", "env")
			fmt.Printf("📝 認証情報が %s に保存されました\n", envFilePath)
		}
	}

	// 出力先の設定
	if outputFile != "" {
		file, err := os.Create(outputFile)
		if err != nil {
			log.Fatalf("出力ファイルの作成に失敗しました: %v", err)
		}
		defer file.Close()

		// JSON 出力
		encoder := json.NewEncoder(file)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(result); err != nil {
			log.Fatalf("結果のエンコードに失敗しました: %v", err)
		}
		fmt.Printf("📄 JSONデータが %s に保存されました\n", outputFile)
	} else {
		// 標準出力にJSON出力
		encoder := json.NewEncoder(os.Stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(result); err != nil {
			log.Fatalf("結果のエンコードに失敗しました: %v", err)
		}
	}
}

// saveToEnvFile は認証情報を .nlm/env ファイルに保存します
func saveToEnvFile(token, cookies, profileName string) error {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("ホームディレクトリの取得に失敗: %w", err)
	}

	// .nlm ディレクトリを作成
	nlmDir := filepath.Join(homeDir, ".nlm")
	if err := os.MkdirAll(nlmDir, 0700); err != nil {
		return fmt.Errorf(".nlm ディレクトリの作成に失敗: %w", err)
	}

	// env ファイルを作成または更新
	envFilePath := filepath.Join(nlmDir, "env")
	content := fmt.Sprintf("NLM_COOKIES=%q\nNLM_AUTH_TOKEN=%q\nNLM_BROWSER_PROFILE=%q\n",
		cookies,
		token,
		profileName,
	)

	if err := os.WriteFile(envFilePath, []byte(content), 0600); err != nil {
		return fmt.Errorf("env ファイルへの書き込みに失敗: %w", err)
	}

	return nil
}

// getAuth は認証情報を取得します
func getAuth(profileName string) (token, cookies string, err error) {
	// 一時的なディレクトリを作成
	tempDir, err := os.MkdirTemp("", "nlm-auth-*")
	if err != nil {
		return "", "", fmt.Errorf("一時ディレクトリの作成に失敗: %w", err)
	}
	defer os.RemoveAll(tempDir) // 終了時に一時ディレクトリを削除

	// プロファイルデータをコピー
	fmt.Println("📋 プロファイルデータをコピーしています...")
	if err := copyProfileData(profileName, tempDir); err != nil {
		return "", "", fmt.Errorf("プロファイルのコピーに失敗: %w", err)
	}

	// ChromeDP の Context 作成
	fmt.Println("🌐 ブラウザを起動しています...")
	opts := []chromedp.ExecAllocatorOption{
		chromedp.NoFirstRun,
		chromedp.NoDefaultBrowserCheck,
		chromedp.DisableGPU,
		chromedp.Flag("disable-extensions", true),
		chromedp.Flag("disable-sync", true),
		chromedp.Flag("disable-popup-blocking", true),
		chromedp.Flag("window-size", "1280,800"),
		chromedp.UserDataDir(tempDir),
		chromedp.Flag("headless", !debug),
		chromedp.Flag("disable-hang-monitor", true),
		chromedp.Flag("disable-ipc-flooding-protection", true),
		chromedp.Flag("disable-prompt-on-repost", true),
		chromedp.Flag("disable-renderer-backgrounding", true),
		chromedp.Flag("force-color-profile", "srgb"),
		chromedp.Flag("metrics-recording-only", true),
		chromedp.Flag("safebrowsing-disable-auto-update", true),
		chromedp.Flag("enable-automation", true),
		chromedp.Flag("password-store", "basic"),
	}

	allocCtx, allocCancel := chromedp.NewExecAllocator(context.Background(), opts...)
	defer allocCancel()

	var ctx context.Context
	if debug {
		ctx, _ = chromedp.NewContext(allocCtx, chromedp.WithLogf(log.Printf))
	} else {
		ctx, _ = chromedp.NewContext(allocCtx)
	}

	// タイムアウト設定
	ctx, cancel := context.WithTimeout(ctx, 60*time.Second)
	defer cancel()

	// 認証情報を抽出
	fmt.Println("🔄 NotebookLMにアクセスしています...")
	return extractAuthData(ctx)
}

// extractAuthData は NotebookLM から認証情報を抽出します
func extractAuthData(ctx context.Context) (token, cookies string, err error) {
	// NotebookLM に移動して初期ページの読み込みを待機
	if err := chromedp.Run(ctx,
		chromedp.Navigate("https://notebooklm.google.com"),
		chromedp.WaitVisible("body", chromedp.ByQuery),
	); err != nil {
		return "", "", fmt.Errorf("ページの読み込みに失敗: %w", err)
	}

	fmt.Println("🔍 認証情報を探しています...")

	// タイムアウト付きコンテキストを作成
	pollCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	dots := 0
	for {
		select {
		case <-pollCtx.Done():
			var currentURL string
			_ = chromedp.Run(ctx, chromedp.Location(&currentURL))
			return "", "", fmt.Errorf("タイムアウト: 認証データが見つかりませんでした (URL: %s)", currentURL)

		case <-ticker.C:
			// 認証データの抽出を試みる
			token, cookies, err = tryExtractAuth(ctx)
			if err != nil {
				if debug {
					deadline, _ := ctx.Deadline()
					remaining := time.Until(deadline).Seconds()
					log.Printf("認証チェックに失敗: %v (残り %.1f 秒)", err, remaining)
				}
				dots = (dots % 3) + 1
				fmt.Printf("\r🔍 認証情報を待機中%s  ", strings.Repeat(".", dots))
				continue
			}
			if token != "" {
				fmt.Println("\r✅ 認証情報を検出しました        ")
				return token, cookies, nil
			}
			dots = (dots % 3) + 1
			fmt.Printf("\r🔍 認証情報を待機中%s  ", strings.Repeat(".", dots))
		}
	}
}

// tryExtractAuth は WIZ_global_data から認証トークンとクッキーを抽出する
func tryExtractAuth(ctx context.Context) (token, cookies string, err error) {
	var hasAuth bool
	err = chromedp.Run(ctx,
		chromedp.Evaluate(`!!window.WIZ_global_data`, &hasAuth),
	)
	if err != nil {
		return "", "", fmt.Errorf("認証データの存在確認に失敗: %w", err)
	}

	if !hasAuth {
		return "", "", nil
	}

	err = chromedp.Run(ctx,
		chromedp.Evaluate(`WIZ_global_data.SNlM0e`, &token),
		chromedp.ActionFunc(func(ctx context.Context) error {
			cks, err := network.GetCookies().WithUrls([]string{"https://notebooklm.google.com"}).Do(ctx)
			if err != nil {
				return fmt.Errorf("クッキーの取得に失敗: %w", err)
			}

			var cookieStrs []string
			for _, ck := range cks {
				cookieStrs = append(cookieStrs, fmt.Sprintf("%s=%s", ck.Name, ck.Value))
			}
			cookies = strings.Join(cookieStrs, "; ")
			return nil
		}),
	)
	if err != nil {
		return "", "", fmt.Errorf("認証データの抽出に失敗: %w", err)
	}

	if token == "" || cookies == "" {
		return "", "", fmt.Errorf("認証トークンまたはクッキーの抽出に失敗")
	}

	return token, cookies, nil
}

// copyProfileData は Chrome プロファイルから必要なファイルをコピーする
func copyProfileData(profileName, tempDir string) error {
	sourceDir := getChromeUserDataDir(profileName)
	if debug {
		log.Printf("プロファイルデータのコピー元: %s", sourceDir)
	}

	// ソースディレクトリが存在するか確認
	if _, err := os.Stat(sourceDir); os.IsNotExist(err) {
		return fmt.Errorf("Chrome プロファイルディレクトリが見つかりません: %s", sourceDir)
	}

	// デフォルトプロファイルディレクトリを作成
	defaultDir := filepath.Join(tempDir, "Default")
	if err := os.MkdirAll(defaultDir, 0755); err != nil {
		return fmt.Errorf("プロファイルディレクトリの作成に失敗: %w", err)
	}

	// 必要なファイルをコピー
	files := []string{
		"Cookies",
		"Login Data",
		"Web Data",
	}

	for _, file := range files {
		src := filepath.Join(sourceDir, file)
		dst := filepath.Join(defaultDir, file)

		if err := copyFile(src, dst); err != nil {
			if !os.IsNotExist(err) {
				return fmt.Errorf("%s のコピーに失敗: %w", file, err)
			}
			if debug {
				log.Printf("存在しないファイルをスキップ: %s", file)
			}
		}
	}

	// 基本的なLocal Stateファイルを作成
	localState := `{"os_crypt":{"encrypted_key":""}}`
	if err := os.WriteFile(filepath.Join(tempDir, "Local State"), []byte(localState), 0644); err != nil {
		return fmt.Errorf("Local State ファイルの作成に失敗: %w", err)
	}

	return nil
}

// copyFile はファイルをコピーする
func copyFile(src, dst string) error {
	source, err := os.Open(src)
	if err != nil {
		return err
	}
	defer source.Close()

	destination, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destination.Close()

	_, err = io.Copy(destination, source)
	return err
}

// getChromeUserDataDir は OS に応じた Chrome のユーザーデータディレクトリを返す
func getChromeUserDataDir(profile string) string {
	var baseDir string

	switch runtime.GOOS {
	case "windows":
		localAppData := os.Getenv("LOCALAPPDATA")
		if localAppData == "" {
			home, _ := os.UserHomeDir()
			localAppData = filepath.Join(home, "AppData", "Local")
		}
		baseDir = filepath.Join(localAppData, "Google", "Chrome", "User Data")
	case "darwin":
		home, _ := os.UserHomeDir()
		baseDir = filepath.Join(home, "Library", "Application Support", "Google", "Chrome")
	case "linux":
		home, _ := os.UserHomeDir()
		baseDir = filepath.Join(home, ".config", "google-chrome")
	default:
		log.Fatalf("サポートされていないOS: %s", runtime.GOOS)
		return ""
	}

	return filepath.Join(baseDir, profile)
}

// getEnvOrDefault は環境変数の値を取得し、設定されていない場合はデフォルト値を返す
func getEnvOrDefault(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
