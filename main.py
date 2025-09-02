from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import os, json, uuid

timeLimit = 10
maxPlayers = 4

@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

@register("成语接龙","X-02Y","一个简单的成语接龙插件","0.0.1")
class ChengyuJielong(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command_group("成语接龙")
    def jielong(self):
        pass

    @jielong.command.command("举行")
    async def jielong_holding(self, event: AstrMessageEvent):
        """开启一局成语接龙会话"""
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 该json文件存储成语接龙的历史记录
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        
        another_file_path = os.path.join(os.path.dirname(__file__), '../../participating_ids.json')
        # 该json文件存储正在参与的用户id
        # 检查发起者是否在参与比赛，如果是则拒绝新建的请求
        with open(another_file_path, 'r', encoding='utf-8') as f:
            try:
                participating_ids = json.load(f)
            except Exception:
                participating_ids = []
        if start_user_id in participating_ids:
            yield event.plain_result(f"你已经在对局中，ID: {competition_id}")
            return
        # 将发起者加入参与者列表
        if os.path.exists(another_file_path):
            with open(another_file_path, 'r', encoding='utf-8') as f:
                try:
                    participating_ids = json.load(f)
                except Exception:
                    participating_ids = []
        else:
            participating_ids = []

        participating_ids.append(start_user_id)
        with open(another_file_path, 'w', encoding='utf-8') as f:
            json.dump(participating_ids, f, ensure_ascii=False, indent=2)

        # 生成唯一对局id
        competition_id = str(uuid.uuid4())
        start_user_id = event.get_sender_id()
        new_competition = {
            "id": competition_id,
            "starter": start_user_id,
            "started": False,
            "ended": False,
            "members_id": {},
            "history": {}
        }
        history.append(new_competition)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"已创建新对局，ID: {competition_id}")

    @jielong.command("参加")
    async def jielong_participate(self, event: AstrMessageEvent, competition_id: str):
        """参加成语接龙"""
        participant_id = event.get_sender_id()
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []

        # 查找对局
        competition = next((c for c in history if c["id"] == competition_id), None)
        if not competition:
            yield event.plain_result(f"对局不存在或已结束，ID: {competition_id}")
            return
        
        # 查看是否超过人数限制
        if len(competition["members_id"]) >= maxPlayers:
            yield event.plain_result(f"对局人数已满，ID: {competition_id}")
            return

        # 检查参与者是否已经在比赛中
        another_file_path = os.path.join(os.path.dirname(__file__), '../../participating_ids.json')
        with open(another_file_path, 'r', encoding='utf-8') as f:
            try:
                participating_ids = json.load(f)
            except Exception:
                participating_ids = []
        if participant_id in participating_ids:
            yield event.plain_result(f"你已经在对局中，ID: {competition_id}")
            return

        # 添加参与者
        competition["members_id"][participant_id] = event.get_sender_name()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"已参加对局，ID: {competition_id}")

    @jielong.command("开始")
    async def jielong_start(self, event: AstrMessageEvent):
        """开始一局成语接龙"""
        # 如果调用命令的用户是一个存在但是尚未开始的比赛的发起者，才开始这比赛
        sender_id = event.get_sender_id()
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        competition = next((c for c in history if c["starter"] == sender_id and not c["started"]), None)
        if not competition:
            yield event.plain_result(f"没有找到可以开始的对局")
            return
        


    @jielong.command("退出")
    async def jielong_quit(self, event: AstrMessageEvent):
        """退出当前的成语接龙"""
        # 检查用户是否在任何尚未结束的比赛中
        participant_id = event.get_sender_id()
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        competition = next((c for c in history if participant_id in c["members_id"] and not c["ended"]), None)
        if not competition:
            yield event.plain_result(f"你不在任何对局中")
            return

    @jielong.command("结束")
    async def jielong_end(self, event: AstrMessageEvent, competition_id: str):
        """结束当前的成语接龙"""
        # 如果调用命令的用户是一个存在的比赛的发起者，才结束这比赛
        sender_id = event.get_sender_id()
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        competition = next((c for c in history if c["id"] == competition_id and c["starter"] == sender_id and not c["ended"]), None)
        if not competition:
            yield event.plain_result(f"没有找到可以结束的对局，ID: {competition_id}")
            return

    @jielong.command("历史")
    async def jielong_history(self, event: AstrMessageEvent, competition_id: str):
        """查看指定对局的历史记录"""
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        competition = next((c for c in history if c["id"] == competition_id), None)
        if not competition:
            yield event.plain_result(f"没有找到对局，ID: {competition_id}")
            return
        # 返回对局的历史记录
        yield event.plain_result(f"对局历史，ID: {competition_id}\n{competition['history']}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @jielong.command("删除")
    async def jielong_delete(self, event: AstrMessageEvent, competition_id: str):
        """删除指定对局（管理员权限）"""
        file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        # 读取历史
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        competition = next((c for c in history if c["id"] == competition_id), None)
        if not competition:
            yield event.plain_result(f"没有找到对局，ID: {competition_id}")
            return
        # 删除对局
        history.remove(competition)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"已删除对局，ID: {competition_id}")
