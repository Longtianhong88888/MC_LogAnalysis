"""使用说明：各制程的使用方法、日志要求与计算逻辑。"""

USER_GUIDE_HTML = """
<h2>MC Log Analysis Tool 使用说明</h2>

<h3>一、基本操作</h3>
<ol>
  <li><b>选择源文件夹</b>：存放机台日志的文件夹（支持子文件夹，按文件名识别机台/模组）。</li>
  <li><b>选择输出文件夹</b>：分析结果（Excel / PPT）输出位置。</li>
  <li><b>选择制程模板</b>：程序会自动预填该制程的 UPH 触发词、报警关键词、制程名称（原因清单）等参数，可按需手动修改。</li>
  <li><b>选择功能</b>：文档合并与内容拆分 / UPH 分析 / EFF 分析 / 报警分析 / 机台状态分析 / 一键分析（自动报告）。</li>
  <li>一键分析（自动报告）只运行 UPH / EFF / 报警 / 状态 4 项并生成 PPT；文档合并与内容拆分需单独选择执行，避免大日志拖慢整体速度。</li>
  <li><b>自动报告</b>：一键运行分析，结果直接显示在界面并导出 Excel/PPT 报告。</li>
</ol>

<h3>二、各制程说明</h3>

<h4>通用（手动配置）/ 自定义</h4>
<p>不套用模板，按界面当前参数分析全部日志；自定义模板可保存常用配置供下次使用。</p>

<h4>LM 激光打标</h4>
<p>以 <b>MarkEnd1</b>（打标完成动作）为产出周期，1 颗/周期。状态/EFF 依赖日志中的 status:RUN/IDLE/DOWN 行；报警用通用关键词。换盘按 JigLoading 间隔平摊到单颗 CT。</p>

<h4>CAW 组装</h4>
<p>以 <b>放熟料完成、放生料完成</b> 为产出周期，1 颗/周期；默认读取 记录PLC、RAYPRUS、Debug、设备状态 相关文件。状态与报警用通用关键词。</p>

<h4>FR 点胶</h4>
<p>左轴/右轴并行工作，分别以 <b>轴点胶完成</b>（漏点产品以 <b>有漏点产品</b> 代替）为单件完成标记，分左轴/右轴两个模组统计；<b>Pure UPH 按 0.5 系数</b>（单轴产能），整机 Derated UPH M1/M2 = 左轴+右轴。EFF/状态按 UDP Module - Good 活动 + AutoRun Stop 停机推导。</p>

<h4>SA 四工位</h4>
<p>点胶/贴附/热压/检测四工位，<b>自动判定瓶颈工位</b>（每排周期最长者），UPH = 每排产品数 × 3600 ÷ 瓶颈有效周期；换盘时间 = 同工位 JigUnloading → JigLoading 间隔，平摊到整盘排数再平摊到单颗 CT。EFF/状态按 UDP Module - Good + AutoRun Stop（EReason 清单匹配区分 uDT/pDT）。</p>

<h4>ACF 三機（上料機 / 主機 / 下料機）</h4>
<p>三部分分文件夹分开统计：</p>
<ul>
  <li><b>上料機</b>：以 <b>更新Carrier盘</b> 为周期（1 次装盘 = 8 颗）；每盘颗数按 carrierId 动态统计（约 8 颗/盘）；换盘时间 = 请求出托盘 → 等待Carrier Ready 间隔。</li>
  <li><b>主機</b>：以 <b>Cavity cnt:1</b> 为周期（1 批 = 8 颗）；carrier 经输送线进出，周期已含换盘。</li>
  <li><b>下料機</b>：以 <b>UnloadDuts Finish</b> 为周期（3 颗/次）；每盘颗数按 CubeTrayId 动态统计（约 24 颗/盘）；换盘时间 = 清除2号托盘 → 轨道2进板成功 间隔。</li>
</ul>
<p>注意：<b>新批次Check 是切 Lot（每批 690 颗），不是换盘</b>，不参与换盘时间计算。EFF/状态按三机活动事件（更新Carrier盘 / Cavity cnt:1 / UnloadDuts Finish）+ 停机事件（ErrOn、生产流程出现异常等）推导整线状态。</p>

<h3>三、计算逻辑</h3>

<h4>UPH（CoreTech AME 定义）</h4>
<ul>
  <li><b>UPH(实际)</b> = 产出数 ÷ 统计时长 × 3600</li>
  <li><b>Pure UPH</b> = 3600 × 每周期产出数 ÷ 理想周期CT（未填理想CT时取正常周期平均）</li>
  <li><b>Derated UPH M2</b> = 3600 × 每周期产出数 ÷ 有效平均周期（剔除 &lt;0.9×理想CT、&gt;1.1×最大理论CT 的离群点）；多模组机台整机 = 各模组 M2 之和</li>
  <li><b>Derated UPH M1</b> = EM 投入数 ÷ RUN 时长（单模组）；多模组整机 = 各模组 M1 之和</li>
  <li><b>有效UPH</b> = 3600 × 每周期产出数 ÷（基础周期 + 每颗换盘开销），其中 每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数</li>
  <li>周期分类：间隔 &gt; 计划性停机阈值 → 计划性停机；&gt; 正常周期阈值 → 异常周期；其余为正常周期。</li>
</ul>

<h4>EFF（CoreTech AME）</h4>
<ul>
  <li><b>EFF(效率)</b> = 操作时间(运行+待机) ÷ 计划生产时间</li>
  <li>状态由日志推导：活动事件（如完成动作）→ RUN；停机事件（AutoRun Stop / ErrOn / 生产流程出现异常）按 EReason 清单归类为 DOWN 或 IDLE。</li>
  <li>停机按 ReasonID 拆分为计划停机 pDT 与非计划停机 uDT，未填计划停机 ReasonID 时全部计入可用性损失。</li>
</ul>

<h4>机台状态分析</h4>
<p>优先识别日志中 status:RUN/IDLE/DOWN 行；无 status 行时按“活动关键词 + 停机关键词”推导状态时间线，统计各状态时长、占比与小时分布。</p>

<h4>报警分析</h4>
<p>按报警关键词命中日志行计数，按机台/模组汇总，输出关键词分布与明细（含 EReason 中文名映射）。</p>

<h3>四、换盘与每盘颗数</h3>
<ul>
  <li><b>每盘颗数</b>：按日志中的 Tray ID（carrierId / CubeTrayId）动态分段统计，不写死。</li>
  <li><b>单次换盘时间</b>：SA 式取“同工位 卸载 → 下一次装载”的间隔中位数（如 SA JigUnloading→JigLoading、ACF 上料機 请求出托盘→等待Carrier Ready、下料機 清除2号托盘→轨道2进板成功）。</li>
  <li>换盘开销按整盘颗数平摊到单颗 CT，避免高估 UPH。</li>
</ul>
"""
