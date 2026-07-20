from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
import httpx
import json

class NewApiCheckinPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.api_url = config.get("api_url", "").strip()
        self.user_id = config.get("user_id", "").strip()
        self.access_token = config.get("access_token", "").strip()
        self.enable_llm = config.get("enable_llm_checkin", True)
        logger.info(f"New-API 签到加载，llm_enabled={self.enable_llm}")

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
                    return f"签到成功"
                else:
                    return f"签到失败 {result.get('message', '未知错误')}"
        except httpx.TimeoutException:
            return "签到失败 请求超时"
        except httpx.RequestError as e:
            return f"签到失败 网络错误"
        except json.JSONDecodeError:
            return "签到失败 API 返回格式异常"
        except Exception as e:
            logger.error(f"签到异常 {e}")
            return f"签到失败 {str(e)}"

    @filter.command("签到")
    async def checkin_cmd(self, event: AstrMessageEvent):
        result = await self._do_checkin()
        yield event.plain_result(result)

    @filter.llm_tool(name="astrbot_plugin_newapi_checkin", description="执行New-API每日签到，获取积分或奖励")
    async def checkin_tool(self, event: AstrMessageEvent):
        if not self.enable_llm:
            return "签到工具未启用，请在插件设置中开启"
        result = await self._do_checkin()
        return result

    async def terminate(self):
        pass