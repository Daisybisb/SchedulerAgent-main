# Deploy Pipeline（SchedulerAgent）

本文檔說明從 GitHub 到 Azure Functions 的自動打包與部署流程，並包含三種視角的圖示（Mermaid）。

## 1) Flowchart

```mermaid
flowchart TD
    A[開發者 push/PR 到 main] --> B[GitHub Actions 觸發 workflow: deploy.yml]
    B --> C[Checkout repository]
    C --> D[Setup Python 3.11]
    D --> E[Install dependencies<br/>pip install -r requirements.txt<br/>pip install pytest pytest-html]
    E --> F[Run tests<br/>PYTHONPATH=${{ github.workspace }} pytest --html=reports/test-report.html]
    
    F -->|測試通過| G[Upload pytest report artifact]
    F -->|測試失敗| Z1[Job 失敗，通知/審查]:::bad

    G --> H[Azure Login (azure/login@v1)<br/>使用 secrets.AZURE_CREDENTIALS]
    H --> I[Package: SchedulerAgent_function<br/>(由 Azure/functions-action 內部打包為 release.zip)]
    I --> J[Deploy to Azure Functions<br/>Azure/functions-action@v1]
    J --> K[Azure Zip Deploy (Kudu)<br/>將 release.zip 上傳到儲存體容器: github-actions-deploy / scm-releases]
    K --> L[Zip 解壓至 /site/wwwroot]
    L --> M[Function Host 重啟與冷啟（Warmup）]
    M --> N[就緒: 端點可用 (/ping, /preview)]
    N --> O[可選: 手動或自動驗證呼叫 API]
    
    classDef bad fill:#ffe5e5,stroke:#ff6b6b,color:#b00020;
