from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import os, json, uuid

@register("成语接龙","X-02Y","一个简单的成语接龙插件","0.0.1","none")
class ChengyuJielong(Star):
    def __init__(self, context: Context,config:AstrBotConfig):
        super().__init__(context)
        self.config = config

    @filter.command_group("成语接龙")
    def jielong(self):
        pass

    @jielong.command("举行")
    async def jielong_holding(self, event: AstrMessageEvent):
        """开启一局成语接龙会话"""
        ready_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ready.json')
        # 读取历史
        if os.path.exists(ready_file_path):
            with open(ready_file_path, 'r', encoding='utf-8') as f:
                try:
                    ready = json.load(f)
                except Exception:
                    ready = []
        else:
            ready = []

        ongoing_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ongoing.json')
        if os.path.exists(ongoing_file_path):
            with open(ongoing_file_path, 'r', encoding='utf-8') as f:
                try:
                    ongoing = json.load(f)
                except Exception:
                    ongoing = []
        else:
            ongoing = []
        
        # check if the starter is already in a ongoing or ready game, where the structure is alike new_competition
        starter_id = event.get_sender_id()
        for competition in ongoing + ready:
            if starter_id in competition["members_id"] or competition["starter"] == starter_id:
                yield event.plain_result(f"你已经在进行中的对局中，ID: {competition['id']}")
                return

        # 生成唯一对局id
        competition_id = str(uuid.uuid4())
        start_user_id = event.get_sender_id()
        new_competition = {
            "id": competition_id,
            "starter": start_user_id,
            "members_id": [],
            "history": [],
            "history_corresponding_player_name":[]
        }
        new_competition["members_id"].append(start_user_id)
        ready.append(new_competition)
        with open(ready_file_path, 'w', encoding='utf-8') as f:
            json.dump(ready, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"已创建新对局，ID: {competition_id}")

    @jielong.command("参加")
    async def jielong_participate(self, event: AstrMessageEvent, competition_id: str):
        """参加成语接龙"""
        participant_id = event.get_sender_id()
        ready_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ready.json')
        # 读取历史
        if os.path.exists(ready_file_path):
            with open(ready_file_path, 'r', encoding='utf-8') as f:
                try:
                    ready = json.load(f)
                except Exception:
                    ready = []
        else:
            ready = []

        # 查找对局
        competition = next((c for c in ready if c["id"] == competition_id), None)
        if not competition:
            yield event.plain_result(f"对局不存在或已结束，ID: {competition_id}")
            return
        
        # 查看是否超过人数限制
        if len(competition["members_id"]) >= maxPlayers:
            yield event.plain_result(f"对局人数已满，ID: {competition_id}")
            return

        # 检查参与者是否已经在比赛中
        ongoing_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ongoing.json')
        if os.path.exists(ongoing_file_path):
            with open(ongoing_file_path, 'r', encoding='utf-8') as f:
                try:
                    ongoing = json.load(f)
                except Exception:
                    ongoing = []
        else:
            ongoing = []

        for competition in ongoing + ready:
            if participant_id in competition["members_id"]:
                yield event.plain_result(f"你已经在对局中，ID: {competition['id']}")
                return

        # 添加参与者
        competition["members_id"].append(event.get_sender_id())
        with open(ready_file_path, 'w', encoding='utf-8') as f:
            json.dump(ready, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"已参加对局，ID: {competition_id}")

    @jielong.command("开始")
    async def jielong_start(self, event: AstrMessageEvent):
        """开始一局成语接龙"""
        # 如果调用命令的用户是一个存在但是尚未开始的比赛的发起者，才开始这比赛
        sender_id = event.get_sender_id()
        ready_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ready.json')
        if os.path.exists(ready_file_path):
            with open(ready_file_path, 'r', encoding='utf-8') as f:
                try:
                    ready = json.load(f)
                except Exception:
                    ready = []
        else:
            ready = []
        competition = next((c for c in ready if c["starter"] == sender_id), None)
        if not competition:
            yield event.plain_result(f"没有找到可以开始的对局")
            return
        # 从ready中删除该场比赛并写回文件
        ready.remove(competition)
        with open(ready_file_path, 'w', encoding='utf-8') as f:
            json.dump(ready, f, ensure_ascii=False, indent=2)
        ongoing_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ongoing.json')
        if os.path.exists(ongoing_file_path):
            with open(ongoing_file_path, 'r', encoding='utf-8') as f:
                try:
                    ongoing = json.load(f)
                except Exception:
                    ongoing = []
        else:
            ongoing = []
        # delete the competition from the ready list and add it to the ongoing list
        player_set = competition["members_id"]
        yield event.plain_result(f"已开始对局，ID: {competition['id']}")
        llm_response = await self.context.get_using_provider().text_chat(
        prompt="随机说出一个四字成语作为开头",
        system_prompt="你是一个成语接龙的游戏助手，负责管理游戏的进行和规则。请给出一个随机的四字成语作为开头"  # 系统提示，可以不传
    )
        start_idiom = llm_response.raw_completion.choices[0].message.content
        competition["history"].append(start_idiom)
        competition["history_corresponding_player_name"].append("小夜")
        ongoing.append(competition)
        yield event.request_llm(
        prompt=start_idiom,
        system_prompt="你现在是成语接龙裁判，负责管理游戏的进行和规则。现在需要告诉大家现在成语接龙的成语是prompt中的成语，并且活泼一点。",
        image_urls=[], # 图片链接，支持路径和网络链接
    )
        with open(ongoing_file_path, 'w', encoding='utf-8') as f:
            json.dump(ongoing, f, ensure_ascii=False, indent=2)


    @jielong.command("退出")
    async def jielong_quit(self, event: AstrMessageEvent):
        """退出当前的成语接龙"""
        # 检查用户是否在任何尚未结束的比赛中
        participant_id = event.get_sender_id()
        ready_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ready.json')
        if os.path.exists(ready_file_path):
            with open(ready_file_path, 'r', encoding='utf-8') as f:
                try:
                    ready = json.load(f)
                except Exception:
                    ready = []
        else:
            ready = []
        ongoing_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ongoing.json')
        if os.path.exists(ongoing_file_path):
            with open(ongoing_file_path, 'r', encoding='utf-8') as f:
                try:
                    ongoing = json.load(f)
                except Exception:
                    ongoing = []
        else:
            ongoing = []
        for competition in ongoing + ready:
            if participant_id in competition["members_id"]:
                competition["members_id"].remove(participant_id)
                yield event.plain_result(f"你已经在对局中，ID: {competition['id']}")
                return
        yield event.plain_result(f"你不在任何对局中")

    @jielong.command("结束")
    async def jielong_end(self, event: AstrMessageEvent, competition_id: str):
        """结束当前的成语接龙"""
        # 如果调用命令的用户是一个存在的比赛的发起者，才结束这比赛
        sender_id = event.get_sender_id()
        # 读取历史
        ongoing_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ongoing.json')
        if os.path.exists(ongoing_file_path):
            with open(ongoing_file_path, 'r', encoding='utf-8') as f:
                try:
                    ongoing = json.load(f)
                except Exception:
                    ongoing = []
        else:
            ongoing = []
        competition = next((c for c in ongoing if c["id"] == competition_id and c["starter"] == sender_id), None)
        if not competition:
            yield event.plain_result(f"没有找到可以结束的对局，ID: {competition_id}")
            return
        # delete the competition from the ongoing list
        ongoing.remove(competition)
        with open(ongoing_file_path, 'w', encoding='utf-8') as f:
            json.dump(ongoing, f, ensure_ascii=False, indent=2)

        history_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_history.json')
        if os.path.exists(history_file_path):
            with open(history_file_path, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        else:
            history = []
        history.append(competition)
        with open(history_file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"已结束对局，ID: {competition_id}")

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
        yield event.plain_result(f"对局历史，ID: {competition_id}")
        history_str = "\n".join([f"{i+1}. {name}: {idiom}" for i, (name, idiom) in enumerate(zip(competition["history_corresponding_player_name"], competition["history"]))])
        yield event.plain_result(history_str)

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

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def jielong_process(self,event:AstrMessageEvent):
        ongoing_file_path = os.path.join(os.path.dirname(__file__), '../../jielong_ongoing.json')
        if os.path.exists(ongoing_file_path):
            with open(ongoing_file_path, 'r', encoding='utf-8') as f:
                try:
                    ongoing = json.load(f)
                except Exception:
                    ongoing = []
        else:
            ongoing = []
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()
        competition = next((c for c in ongoing if sender_id in c["members_id"]), None)
        if not competition:
            return
        idiom = event.message_str
        if(idiom.find("成语") != -1):
            yield event.plain_result(f"请输入成语")
            return
        last_idiom = competition["history"][-1] if competition["history"] else ""
        if(last_idiom == ""):
            yield event.plain_result(f"成语接龙还未开始，请等待发起人开始")
            return
#        yield event.plain_result(f"调试：正在分析：old idiom: {last_idiom}, new idiom:{idiom}")
        judge_idiom_raw = await self.context.get_using_provider().text_chat(
            prompt = f"""old idiom: {last_idiom}, new idiom:{idiom}""",
        system_prompt="""
            你是一个成语接龙裁判，你要判断用户的输入是否是包含符合规则的成语，即，并返回一个json对象，其结构为：
            {
                "is_valid": True/False,
                "idiom": "<成语>"
            }
            例：
            ########## start of example #############
            input: "old idiom: 江山如画, new idiom: 画龙点睛如何？"
            output: {
                "is_valid": True,
                "idiom": "画龙点睛"
            }
            ########## end of example #############
            ########## start of example #############
            input: "old idiom: 江山如画, new idiom: 虎虎生风这个成语可以"
            output: {
                "is_valid": False,
                "idiom": "虎虎生风"
            }
            ########## end of example #############
            """)
        judge_idiom = judge_idiom_raw.raw_completion.choices[0].message.content
        judge_idiom = json.loads(judge_idiom)
            # use json to parse judge_idiom
            #
        yield event.plain_result(judge_idiom['is_valid'])
        if str(judge_idiom['is_valid']) != 'True':
            yield event.plain_result(f"成语不符合规则，请重新输入")
            return
        idiom = judge_idiom["idiom"]
        competition["history"].append(idiom)
        competition["history_corresponding_player_name"].append(sender_name)
        with open(ongoing_file_path, 'w', encoding='utf-8') as f:
            json.dump(ongoing, f, ensure_ascii=False, indent=2)
        yield event.plain_result(f"成语接龙成功，当前成语链：{' -> '.join(competition['history'])}")
