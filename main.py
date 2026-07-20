from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from pydantic import Field
from pydantic.dataclasses import dataclass
import httpx
import json

@register("astrbot_plugin_newapi_checkin", "your_name", "New-API 每日签到", "1.0.0")
class NewApiCheckinPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # 读取配置
        self.api_url = (config.get("api_url") or "").strip()
        self.user_id = (config.get("user_id") or "").strip()
        self.access_token = (config.get("access_token") or "").strip()
        self.enable_llm_tool = config.get("enable_llm_checkin", True)
        
        logger.info(f"New-API 签到加载，llm_enabled={self.enable_llm_tool}")
        
        # 如果启用 LLM 工具，则注册
        if self.enable_llm_tool:
            checkin_tool = CheckinTool(plugin=self)
            self.context.add_llm_tools(checkin_tool)

    async def _do_checkin(self) -> str:
        if not self.api_url or not self.user_id or not self.access_token:
            return "请先在插件设置中配置相关信息"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "New-Api-User": str(self.user_id),
                    "Content-Type": "application/json"
                }
                response = await client.post(
                    f"{self.api_url.rstrip('/')}/api/user/checkin",
                    headers=headers
                )
                result = response.json()
                if result.get("success"):
                    return "签到成功"
                else:
                    return f"签到失败 {result.get('message', '未知错误')}"
        except httpx.TimeoutException:
            return "签到失败 请求超时"
        except httpx.RequestError as e:
            return "签到失败 网络错误"
        except json.JSONDecodeError:
            return "签到失败 API 返回格式异常"
        except Exception as e:
            logger.error(f"签到异常 {e}")
            return f"签到失败 {str(e)}"

    @filter.command("签到")
    async def checkin_cmd(self, event: AstrMessageEvent):
        result = await self._do_checkin()
        yield event.plain_result(result)

    async def terminate(self):
        pass

@dataclass
class CheckinTool(FunctionTool[AstrAgentContext]):
    name: str = "astrbot_plugin_newapi_checkin"
    description: str = "执行New-API每日签到，获取积分或奖励"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
        }
    )
    plugin: object = Field(default=None, repr=False)

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        if not self.plugin:
            return "插件未正确初始化"
        # 检查是否启用 LLM 工具
        if not self.plugin.enable_llm_tool:
            return "签到工具未启用，请在插件设置中开启"
        result = await self.plugin._do_checkin()
        return result