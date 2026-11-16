"""H5 component semantics only; media/output contracts remain unchanged."""
ICON_MAP = '反馈与工具图标：答对cb-icon-correct、答错cb-icon-incorrect、已得星cb-icon-star、未得星cb-icon-star-empty、提示cb-icon-hint、画笔cb-icon-pencil、橡皮擦cb-icon-eraser、撤销上一步cb-icon-undo。仅在任务需要且当前能力允许时使用；星星图标不授权新增评分或奖励。学生录音模式为none时仍禁止星级等评测结果，真实操作的温和正误反馈可保留；非none也不因有图标而新增评测。'
SEMANTICS = '普通文字按钮默认左图标、右文字，整体居中；上一题为左箭头＋文字，下一题为文字＋右箭头，箭头绑定实际题目导航。按钮可见文字使用本课指定学科字体，不被组件样式覆盖。英文Retry只重试当前题或步骤，Try again用于已规划的整轮活动重玩并重置本轮进度及已有合法结果；重玩不改变场景边界或单场预览隔离；用户指定文案优先。结果已展示后不再增加Done／完成二次确认；必要的主动提交或结束入口保留，文案写实际动作，完成状态用非交互标签。'
FEEDBACK = '选项内正误符号直接嵌入，不另套圆底、边框、阴影或cb按钮基类；反馈不是按钮，不添加无意义点击。独立反馈确需增强识别时才使用底座。提供可见文案或可访问名称，不只靠颜色表达结果。提示、画笔、橡皮擦、撤销只用于已规划功能；撤销仅恢复上一步，不能代表清空全部或重试，缺少匹配图标时使用同风格SVG。'
RENDER = '反馈图标可独立使用<span class="cb-icon cb-icon-correct" aria-hidden="true"></span>；其他反馈替换对应类名。cb-feedback与cb-stars仅组织布局及配色，不是图标显示的前提；cb-feedback-symbol仅用于确需底座的独立反馈。图标实际大小用width/height设置，不以font-size代替；例如.cb-stars .cb-icon{width:120px;height:120px}，尺寸仍按本课布局确定。图文间距使用gap或单侧margin之一，不重复叠加；保留图标遮罩、比例和清晰颜色。'
PLAN = '在相关h5.contentDescription写明实际需要的反馈、文案、触发条件、按钮动作范围、图标类名与实现结构、尺寸和是否有底座；仅在允许且确有星级玩法时说明数量与计取规则。普通H5的taskDetails、codeTasks、bugList和SDK接口不属于本课输出协议，不引入这些字段或调用。'
CHECK = '核对本课实际用到的控件：按钮图文顺序、实际字体和完整底座；反馈图标有尺寸、颜色及遮罩来源，未被页面样式清空；选项无多余底座，间距不叠加；撤销／清空、单题重试／整轮重玩与真实事件一致；必要提交入口仍在。只有图标类名不等于真实渲染已验证；没有浏览器证据不据此判失败，也不宣称已实测。保持isPassReview与bugDescription两字段输出。'
LIMIT = '仅本轮涉及H5按钮、反馈或工具时应用上述规则，修复其接入与必要联动；保持原题目、答案、已确认玩法、无关工具及媒体播放链，不为图标同步重做全部页面。不因课件使用星星图形推断已授权评分，不改学生录音模式或上报协议。'

def additions(k):
    if k not in ['P4','P5','P6','P7','R1']:return []
    body = '\n'.join([ICON_MAP, SEMANTICS, FEEDBACK, RENDER])
    if k == 'P4':body+='\n'+PLAN
    elif k == 'P6':body+='\n'+CHECK
    elif k in ['P7','R1']:body+='\n'+LIMIT
    return [('图标加文字按钮使用cb-text',body)]
