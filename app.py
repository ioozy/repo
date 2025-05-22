print("👉 This is integratescambot-main version")

from flask import Flask, jsonify
from config import Config
from utils.logger import app_logger as logger
from utils.error_handler import AppError, ConfigError
from services.conversation_service import ConversationService
from services.domain.detection.detection_service import DetectionService
from clients.line_client import LineClient
from clients.analysis_api import AnalysisApiClient
from bot.line_webhook import line_webhook, LineWebhookHandler

def create_app():
    app = Flask(__name__)

    # 載入 .env
    from dotenv import load_dotenv
    load_dotenv()

    # 驗證設定
    try:
        Config.validate()
    except ValueError as e:
        raise ConfigError(f"配置錯誤: {str(e)}", original_error=e)

    # 初始化 line client
    line_client = LineClient(Config.LINE_CHANNEL_ACCESS_TOKEN)

    # 初始化分析 API client（可選）
    analysis_client = None
    if Config.ANALYSIS_API_URL:
        analysis_client = AnalysisApiClient(Config.ANALYSIS_API_URL)

    # 初始化 service 與 handler
    detection_service = DetectionService(analysis_client)
    conversation_service = ConversationService(detection_service=detection_service, line_client=line_client)
    webhook_handler = LineWebhookHandler(conversation_service=conversation_service, channel_secret=Config.LINE_CHANNEL_SECRET)

    # 將 handler 設定到藍圖
    line_webhook.webhook_handler = webhook_handler

    # 註冊藍圖（不要重複）
    app.register_blueprint(line_webhook)

    # 錯誤處理器
    @app.errorhandler(AppError)
    def handle_app_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    # 健康檢查
    @app.route("/")
    def index():
        return "詐騙檢測機器人正在執行中!"

    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "ok",
            "services": {
                "line_client": "ok",
                "detection_service": "ok"
            }
        })

    return app

# 啟動 Flask
try:
    app = create_app()
except Exception as e:
    logger.critical(f"無法創建應用程式: {str(e)}")
    raise

if __name__ == "__main__":
    port = Config.PORT
    debug = Config.DEBUG
    logger.info(f"詐騙檢測機器人啟動於埠口 {port} (除錯模式={debug})")
    try:
        app.run(host="0.0.0.0", port=port, debug=debug)
    except Exception as e:
        logger.critical(f"運行應用程式時發生錯誤: {str(e)}")
        raise
