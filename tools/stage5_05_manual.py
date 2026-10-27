"""Compile one matching Markdown/Word source from real reports, code and evidence."""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]

def block(path,token=None):
 text=(ROOT/path).read_text(encoding='utf-8-sig')
 if token is None:return text
 start=text.index(token);pos=text.index('{',start);depth=0;state='code';i=pos
 while i<len(text):
  c=text[i];next=text[i:i+2]
  if state=='line':
   if c=='\n':state='code'
  elif state=='comment':
   if next=='*/':state='code';i+=1
  elif state in {'"',"'"}:
   if c=='\\':i+=1
   elif c==state:state='code'
  elif next=='//':state='line';i+=1
  elif next=='/*':state='comment';i+=1
  elif c in {'"',"'"}:state=c
  elif c=='{':depth+=1
  elif c=='}':
   depth-=1
   if depth==0:
    end=i+1
    if text[end:end+1]==';':end+=1
    return text[start:end]+'\n'
  i+=1
 raise ValueError((path,token,'unbalanced function'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args()
 local=ROOT/'reports/stage5_05_local';validation_path=local/'validation_summary.json'
 validation=json.loads(validation_path.read_text(encoding='utf-8')) if validation_path.exists() else None
 if not a.allow_incomplete:assert validation and validation['all_checks_passed'],'Do not publish an unverified final manual'
 sections=[];sources=[]
 def add(text):sections.append(text.strip()+'\n\n')
 def source(path,token=None):
  text=block(path,token);sources.append({'file':path,'symbol':token,'file_sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'extracted_sha256':hashlib.sha256(text.encode()).hexdigest(),'lines':len(text.splitlines())})
  add('### 完整关键源码 '+path+((' '+token) if token else ''))
  add('```'+('cmake' if path=='CMakeLists.txt' else 'cpp')+'\n'+text.rstrip()+'\n```')
 def document(path,level=1):
  text=(ROOT/path).read_text(encoding='utf-8')
  if path=='docs/stage5_02_performance.md':
   lines=text.splitlines();result=[];i=0
   while i<len(lines):
    if lines[i].startswith('| case | 推理峰值 / TTS 峰值 |'):
     table=[]
     while i<len(lines) and lines[i].startswith('|'):
      cells=[x.strip() for x in lines[i].strip('|').split('|')]
      if not all(re.fullmatch(r':?-+:?',x) for x in cells):table.append(cells)
      i+=1
     for title,indices in [('峰值与退出状态',[0,1,2,7]),('实际执行 完整交付与策略终态',[0,3,4,5,6])]:
      result+=['','### '+title,'','| '+' | '.join(table[0][k] for k in indices)+' |','|'+'---|'*len(indices)]
      result+=['| '+' | '.join(row[k] for k in indices)+' |' for row in table[1:]]
      result.append('')
    else:result.append(lines[i]);i+=1
   text='\n'.join(result)
  if path=='docs/stage5_05_final_acceptance.md':
   compact=[]
   for line in text.splitlines():
    if line.startswith('| final_'):
     cells=[x.strip() for x in line.strip().strip('|').split('|')]
     if len(cells)==4 and 'devices=' in cells[3]:
      import ast
      offset=cells[3].find('{')
      counters=ast.literal_eval(cells[3][offset:]) if offset>=0 else {}
      prefix=cells[3][:offset].rstrip(' ;；') if offset>=0 else cells[3]
      keys=['dispatched','accepted','rejected','inflight','tts_cancelled','tts_expired']
      summary=', '.join(k+'='+str(counters[k]) for k in keys if k in counters)
      cells[3]=prefix+'; '+(summary or 'preflight rejected; program not started')
      if cells[2]!='None':cells[2]=format(float(cells[2]),'.3f')
      line='| '+' | '.join(cells)+' |'
    compact.append(line)
   text='\n'.join(compact)
  text=re.sub(r'^(#{1,5}) ',lambda m:'#'*min(6,len(m[1])+level)+' ',text,flags=re.M)
  add(text)
 add('# RK3576 端侧多模态系统集成与性能优化工程手册')
 add('本手册面向Linux C++与嵌入式AI工程学习、复现和项目验收，覆盖RK3576上的Camera、ASR、Qwen、SmolVLM2、Kokoro、异步任务、性能测量、Qt与稳定性。5.1～5.4已经用户验收；5.5的最终审核以本节验收清单及真实日志为准。隔离版本没有覆盖主工程。')
 if a.allow_incomplete:add('当前为编写中的完整工作稿。5.5尚在执行，缺失项不作为通过；交付时将根据最终验证重新生成。')
 else:add('本版已完成记录场景内的工程验证，等待用户对最终项目审核。未独立测量的声学延迟、精确首Token与可靠NPU利用率继续保留为空；有限长测不等于任意工况的永久稳定保证。')
 add('<!-- WORD_TOC -->')
 add('<!-- PAGE_BREAK -->')
 add('## 1 工程环境与证据规则')
 add('硬件为LubanCat 3 RK3576，4个Cortex A53和4个Cortex A72，约4GB物理内存、当前无Swap；Linux 6.1.99-rk3576、aarch64、Debian GCC12.2.0、CMake/CTest3.25.1。IMX415通过V4L2 `/dev/video11`采集3840×2160 NV12，stride3840、sizeimage12441600，四个MMAP驱动槽。HyperX Cloud III每次动态发现，历史实际ID为III，不能把历史数字声卡写死。')
 add('| 模块 | 真实模型或Runtime | 执行与限制 |\n|---|---|---|\n| ASR | Silero VAD与SenseVoice INT8，sherpa onnx1.13.8 | CPU；实时采集与预分段回放必须区分 |\n| TEXT | Qwen2.5 1.5B W4A16，RKLLM1.3.1 | 模型制品toolkit1.2.3；RKNPU driver0.9.8 |\n| VISION | SmolVLM2 256M W4A16加scatterfix RKNN Vision | RGB512×512，64×576浮点特征；语言制品toolkit1.3.1 |\n| TTS | Kokoro multi lang v1_1，ORT1.28.2 | CPU，sid17，speed1，silence_scale0.2，24kHz |\n| Qt | Qt5.15.8 Widgets与Test | 可选构建，现有xcb桌面，不安装新软件 |')
 add('原稳定目录是`/home/cat/projects/RK3576/rk3576_multimodal`，唯一授权写目录是其同级`rk3576_multimodal_stage5_review`。模型及SDK继续引用原路径，源码和构建使用新目录。根目录历史笔记和早期architecture/run文档不能替代源码或终端；没有Git仓库时使用真实git diff no-index并验证补丁，不虚构commit。')
 add('```bash\n'+(ROOT/'tools/stage5_board_paths.sh').read_text(encoding='utf-8').split('stage5_cache_value()',1)[0].rstrip()+'\n```')
 add('路径变量只是环境引用，不复制模型。`source`影响当前shell，`set -a`使变量导出到子进程；LD_LIBRARY_PATH仅为本次进程指定已存在共享库，不修改系统缓存。每次实际参数、版本、声卡、PID、退出码、原工程指纹都与对应case共同保留。')
 add('## 2 开发时间线与最终系统关系')
 add('| 阶段 | 时间依据 | 具体目标与结果 |\n|---|---|---|\n| 5.1 | 2026年10月17日报告及SSH日志 | 生命周期审计、RKLLM回调/输出释放、协作式SIGINT和SIGTERM |\n| 5.2 | 2026年10月17日报告及ARM日志 | ASR解耦、共同推理FIFO、有界背压、取消与排空 |\n| 5.3 | 2026年10月17日报告及固定帧 | 三槽自有帧池、缓存预处理，RGA失败保留 |\n| 5.4 | 2026年10月17日固定输入与听音 | 统一请求计时、TTS2/4线程同条件n30比较 |\n| 5.5 | 2026年10月17日晚至18日实测 | Qt适配、热对照、最终源码长测、异常与完整交付 |')
 add('最终语音入口直接使用IntentRouter，没有经过另一个CLI中的RequestProcessor。Camera、采集/VAD、ASR、推理、TTS和信号接收分别承担职责。InferenceWorker是include/ai/llm_worker.h中的using别名，实际实现为src/ai/llm_worker.cpp的LLMWorker，并不存在另一个inference_worker.cpp。TEXT和VISION共用同一个推理消费者；ASR只提交，不同步执行VLM。TTS仍先合成完整PCM再播放，下一条不能越过当前合成和drain。本节没有引入新的AI框架或模型。')
 for name,caption in [('system_architecture','最终进程和线程架构'),('buffer_lifecycle','Camera到VLM的所有权生命周期'),('shutdown_order','安全退出和资源释放顺序')]:
  if (local/'plots'/f'{name}.png').exists():add(f'![{caption}](../reports/stage5_05_local/plots/{name}.png)')
 add('## 3 第五阶段 5.1 生命周期审计和安全退出')
 add('审计首先发现两个真实入口、Worker对Service的借用、lambda引用捕获以及SDK回调状态的寿命边界。join只等待，不通知；开放空ASR队列会使析构永久等待。正确顺序是停止输入并关闭/唤醒队列，join使用者，再销毁Service和Runtime。5.1原完整语音入口没有协作式信号处理，先记录真实缺陷，再最小修复，不能把SIGKILL叫安全退出。')
 add('RKLLM的Pimpl保存参数和callback，析构先destroy handle，随后成员才析构；每次同步run的RunContext与用户callback状态持续到run返回。RKNN输出只在outputs_get成功后归owner，业务先复制Embedding，再在正常/异常退栈路径release。release自身仍可能失败，当前记录错误；这不是SDK所有内部失败路径的证明。')
 source('include/app/stop_signals.h')
 source('src/ai/rkllm_backend.cpp','struct RunContext')
 source('src/ai/rkllm_backend.cpp','int onRKLLMResult(')
 source('src/ai/rkllm_backend.cpp','struct RKLLMBackend::Impl')
 source('src/ai/rk3576_vlm_backend.cpp','struct RknnOutputOwner')
 source('src/audio/asr_service.cpp','bool ASRService::recognize(')
 source('src/audio/asr_pipeline.cpp','void ASRWorker::run()')
 source('src/audio/asr_pipeline.cpp','void ASRWorker::runImpl()')
 add('语法与执行次序：`std::thread(&ASRWorker::run,this)`借用对象地址，因此对象必须活到join之后。入口catch捕获标准和未知异常，设置错误并关闭队列；不能让异常穿出线程入口触发terminate。`lock_guard`在return或异常时自动解锁；`unique_lock`允许condition_variable临时释放并重新获取锁。状态与谓词在同一mutex下更新，notify_all使空队列等待者重新判断closed；通知本身不是可累计事件。')
 add('`StopSignals`在所有线程创建前阻塞SIGINT/SIGTERM，普通线程调用sigtimedwait，atomic发布首个信号。析构置finished、join、恢复原mask。没有handler调用Qt、日志、malloc、mutex或join。构造/析构应由同一owner线程执行。活动同步推理仍允许完成；无法保证闭源SDK永久卡住时存在硬截止。')
 add('5.1最终实机注册CTest4/4、完整TEXT/VISION语音、实际耳机、自然及信号退出和321项保护检查通过。Windows当时6/6只证明portable逻辑，不能替代ARM64。完整缺陷原表现、修复diff和日志在stage5_01_board_acceptance及相应reports目录。')
 add('### 本节面试题与完整答案')
 old=(ROOT/'docs/stage5_01_architecture_audit.md').read_text(encoding='utf-8')
 old=old[old.index('### 1. 为什么只使用智能指针'):old.index('### 下一步',old.index('### 1. 为什么只使用智能指针'))]
 add('以下问题保留5.1当时语境，其Windows6项计数与当时双Engine并发问题不是最终版本现状。')
 add(old)
 add('### 9 为什么不能在signal handler中调用条件变量\n\nPOSIX异步信号可能打断持有同一锁的线程；mutex、condition_variable和Qt操作不保证异步信号安全，会死锁或破坏运行状态。本项目通过阻塞信号加普通sigwait线程，把通知和停止放回正常线程上下文。')
 add('### 10 析构顺序为什么是并发接口的一部分\n\n局部对象逆声明顺序析构，成员也逆声明顺序析构。Worker持有的引用不会自动延长Service、mutex或counter寿命；必须在析构依赖对象前stop/join。只把句柄换成智能指针而不检查谁仍在使用它，仍可能造成use-after-free。')
 add('## 4 第五阶段 5.2 有界异步任务和NPU调度')
 document('docs/stage5_02_async_pipeline.md',1)
 document('docs/stage5_02_performance.md',1)
 add('前文是5.2当时完成记录；其“后续5.3”属于时间线。最终仍复用同一队列和Worker，而非两套并行Demo。')
 source('include/ai/llm_worker.h')
 source('src/ai/llm_worker.cpp')
 source('include/app/pipeline_admission.h')
 source('src/audio/tts_worker.cpp','void TTSWorker::run()')
 document('docs/stage5_02_statement_notes.md',1)
 add('### 核心实测取舍\n\n真实SDK每类n3：顺序Qwen调用均值945.432ms，重叠时2338.717ms；Vision加Smol从1927.090ms到2667.267ms。6/6对均成功，所以没有证明并行必崩；选择共同消费者是降低竞争、明确顺序与背压。异步VISION回调1737.730ms到0.034758ms是提交阻塞改善，不能当VLM推理变成0.035ms。')
 add('5.2 ARM64 CTest5/5，所有是Fake/确定性逻辑测试；真实耳机和交替/连续输入另行验证。过载可以拒绝输入或过期旧任务，必须统计全部终态。推理成功率的分母是实际执行，语音交付率的分母是全部输入，不能混用。')
 add('## 5 第五阶段 5.3 Camera内存和预处理')
 add('V4L2采用MMAP，不是DMA-BUF。DQBUF后按实际plane stride/size复制到自有NV12，再QBUF。驱动随即可以重用映射内存，因此异步VLM不能借用映射裸指针。LatestFrameBuffer发布/读取只交换共享指针，没有每次再复制整帧；CPU预处理融合NV12到RGB和Resize，单独转换与Resize时间未拆分。')
 add('每帧仍有一次12,441,600字节自有NV12复制，按需生成786,432字节RGB，SDK输入内部转换/复制不透明，Vision输出复制147,456字节浮点Embedding。池有三槽，空闲是unique_ptr独占，发布是shared_ptr<const ImageFrame>，最后强引用释放才归还。每次lease新建控制块，旧weak_ptr不能在地址复用后复活。池满只做DQBUF/QBUF并计数，不无界分配。')
 source('include/video/owned_frame_pool.h')
 source('src/video/latest_frame_buffer.cpp')
 source('src/video/image_preprocessor.cpp')
 source('src/ai/rk3576_vlm_backend.cpp','InferenceResult RK3576VLMBackend::infer(')
 document('docs/stage5_03_statement_notes.md',1)
 add('| 5.3指标 | 优化前 | 优化后 | 统计边界 |\n|---|---|---|---|\n| 融合预处理平均/P50/P95 ms | 11.052/10.540/12.640 | 8.325/8.378/9.495 | 各n12，含首次调用 |\n| 显式NV12复制平均ms | 9.459 | 9.736 | 每帧仍一次全帧复制，没有加速 |\n| Frame Age平均ms | 26.851 | 28.384 | 各n9，剔除前三个保存fixture请求，未改善 |\n| RKNN run平均ms | 1160.708 | 1163.491 | 各n12，模型计算没有加速 |\n| Vision进程采样RSS峰值MiB | 554.426 | 552.043 | 非完整多模态进程，不宣称大幅省内存 |')
 add('预处理平均下降24.67%，约2.727ms，不等于完整语音按比例加速。暖态源码可见每帧分配点5降1，最终636次acquire、633次复用、3帧创建、0满池，停止in_use=0；每次lease控制块仍分配，不是零分配。RGA三条硬件路径首job失败，未用于生产；未实现端到端零拷贝。NV12元数据Full Range与原limited算法的既有差异、模型内部mean/std未反查等限制保留，优化只要求与原CPU路径回归一致。')
 document('docs/stage5_03_interview.md',1)
 add('## 6 第五阶段 5.4 统一Profiling和TTS优化')
 add('统一使用steady_clock，Request ID随AudioSegment、TaskOptions及完成回调传递。scope恢复线程局部上下文，SDK回调显式携带共享Trace，没有全局无界请求map。Frame ID和Request ID不同，不能拼错。每次请求记录VAD检测与端点、ASR队列与推理、路由、推理队列/执行、首文本chunk、整段答案、TTS队列/合成、首音频回调、自有PCM、ALSA首次成功提交及drain。')
 add('SDK首个非空文本chunk不等于精确首token；首音频callback只保证一批借用float，当前实现仍等待完整生成再播放。ALSA首次writei提交与drain不是耳机真实声学输出。ASR API包括stream、AcceptWaveform、Decode与取文本；VAD采样索引给出的是主机时间估算，XRUN使其无效。所有缺失观测保持未测量，不能用0或文本长度推算。')
 source('include/common/request_trace.h')
 source('include/common/image_profile.h')
 source('src/audio/tts_service.cpp','bool TTSService::synthesize(')
 source('src/audio/alsa_playback_service.cpp','bool AlsaPlaybackService::play(')
 document('docs/stage5_04_statement_notes.md',1)
 add('| 固定文本 每语言n30 | 2线程平均/P50/P95 ms | 4线程平均/P50/P95 ms | 平均RTF前后 |\n|---|---|---|---|\n| 一加一等于二 | 9945.095/9952.273/10112.211 | 6920.197/6925.889/7042.744 | 5.090→3.545 |\n| A computer monitor displaying a webpage with some text and images | 17758.202/17730.550/18084.155 | 12476.125/12473.974/12609.867 | 4.316→3.032 |')
 add('同一台板、同一冻结5.3 TTS库和benchmark、同模型、sid17、speed1、silence_scale0.2及相同文本；唯一参数差为线程数。每种语言另记first-use与warmup，不混入30暖态样本。中文与英文平均合成耗时分别下降30.42%和29.74%，RTF仍大于1；CPU约199.65%到398.44%（单核100%），最高观测温度76.692℃到85.888℃。这是短时合成收益及资源代价，不是所有子系统都变快。')
 add('独立ORT诊断6次中model_run累计占Generate API约99.9766%，支持主要瓶颈为计算；文本前端/音素化没有独立回调，残差不能叫纯音素化时间。没有重复初始化，因此没有编造“去掉重加载”的收益。1线程更慢，6线程中文更慢且CPU更高，原实验保留未采用。没有更换声音、语速、截断回答或增加并发合成实例。')
 add('同音频/固定帧三组VISION→TEXT有限观测：VISION从ASR入队至drain均值19.914→16.693秒，TEXT29.630→24.334秒；两边均使用60秒TTS等待和180秒期限，避免靠过期制造收益。TEXT模型服务本身1149.5→1422.1ms有回退，不能藏在总延迟下降中。生产12秒/45秒默认策略仍保留。')
 for name,caption in [('tts_latency','5.4固定文本暖态合成分布'),('tts_rtf_cdf','5.4 RTF实测分布')]:add(f'![{caption}](../reports/stage5_04_local/plots/{name}.png)')
 document('docs/stage5_04_interview.md',1)
 add('## 7 第五阶段 5.5 Qt和持续稳定性')
 add('5.5的真实问题、热条件、失败记录、所有版本与验收边界以本节报告为准。下面引用的工作记录在正式生成时与最终数据同步；不把较早热对照源码冒充最后GUI/结构化文本修复的精确版本。')
 document('docs/stage5_05_final_acceptance.md',1)
 document('docs/stage5_05_statement_notes.md',1)
 document('docs/stage5_05_line_notes.md',1)
 for path in ['include/gui/backend_session.h','src/gui/backend_session.cpp','include/gui/session_window.h','src/gui/session_window.cpp','src/gui/main.cpp']:
  source(path)
 source('src/audio/asr_llm_tts_smoke.cpp')
 document('docs/stage5_05_interview.md',1)
 add('## 8 构建运行复现和重要命令')
 document('README_STAGE5_FINAL.md',1)
 if (ROOT/'docs/stage5_05_commands.md').exists():document('docs/stage5_05_commands.md',1)
 else:add('正式命令章节将在最终ARM64、Qt与长测结束后，从command.json和原始退出码生成；当前没有补造输出。')
 add('### 5.3 重要采集 固定帧和RGA命令')
 document('docs/stage5_03_commands.md',2)
 add('### 5.4 固定输入与ORT诊断重要命令')
 old_commands=(ROOT/'docs/stage5_04_commands.md').read_text(encoding='utf-8')
 old_sections=re.split(r'(?m)(?=^## )',old_commands)
 for old_section in old_sections:
  if any(old_section.startswith('## 操作 '+name) for name in ['raw_tts_baseline_2t/run','raw_tts_final_4t/run','baseline_asr_30/run','baseline_vision_30/run','baseline_tts_ort_detail/run','candidate_pipeline_pairs_4t/run']):
   add(re.sub(r'^(#{1,5}) ',lambda m:'#'*min(6,len(m[1])+2)+' ',old_section,flags=re.M))
 add('所有源码/构建/报告目录必须新建且不存在。源码包先核对SHA和安全相对路径，普通cat用户构建；磁盘低于500MiB停止，不删除历史文件腾空间。主工程、模型、SDK、驱动、设备树和内核保持只读。复现时使用新label/case，不直接重跑会覆盖同名证据的命令。')
 add('## 9 最终验收边界和局限')
 add('最终版本不得自动覆盖主稳定工程。Windows CTest、Fake/Mock、真实SDK固定输入、自然麦克风/耳机与GUI交互分别计数；同一请求ID必须带case或会话名。热对照与最终GUI长测标明源码版本、时长、输入间隔、冷却条件和保护停止。原始失败保留，若4线程触发测试护栏必须如实选择默认配置并重测，不能把强杀当优雅退出。')
 add('未测量或未实现：真实声学输出延迟、精确token粒度TTFT、可信NPU利用率/带宽/功耗、完整SDK内部故障注入、DMA-BUF端到端零拷贝、成功RGA生产路径、AEC/PTT/语音打断和任意环境下的永久稳定性。有限RSS稳定不是所有代码无泄漏证明，Linux trip不等于芯片额定安全阈值。')
 add('## 10 简历项目描述与面试讲述')
 add('项目描述可写为：在RK3576端侧集成USB语音采集、Silero VAD、SenseVoice、Qwen2.5、IMX415、RKNN加SmolVLM2、Kokoro与ALSA，完成普通/视觉语音交互。使用C++17 RAII、条件变量、有界Worker及跨阶段额度管理请求寿命，提供协作SIGINT/SIGTERM和可选Qt异步控制页面。')
 add('可核验性能成果：将同步VLM从ASR回调解耦，受控VISION提交由1737.730ms变为0.034758ms，此为调度改善；缓存CPU预处理在n12比较中平均下降24.67%；固定中英文各n30的4线程TTS合成平均耗时分别下降30.42%与29.74%，同时记录近双倍CPU和温度代价。持续稳定性与最终默认线程数必须附5.5真实条件，不能只写“全链路提速30%”。')
 add('面试叙述顺序：先画实际线程和所有权图，解释ASR阻塞与回调寿命问题；再给出有界队列和取消/排空契约；用固定输入、样本量和原始日志说明局部优化；最后主动说明RGA失败、没有零拷贝、TTS仍非实时以及热稳定性的取舍。不要宣称训练了这些模型、修改了驱动或实现了尚无证据的功能。')
 add('## 11 结果索引和源码一致性')
 add('本手册正文是Word与Markdown的共同来源。完整逐文件源码附录、Git格式diff、逐文件SHA、补丁apply检查和字节roundtrip、原始终端日志、CSV/JSON、真实GUI截图、输入及环境清单随最终归档交付。所选关键函数代码从当前真实文件抽取，文件和片段SHA记录在`reports/stage5_05_local/manual_source_manifest.json`，不使用省略号代替函数体。')
 if validation:add('```json\n'+json.dumps({'all_checks_passed':validation.get('all_checks_passed'),'user_acceptance_pending':True,'validation_summary':'reports/stage5_05_local/validation_summary.json'},ensure_ascii=False,indent=2)+'\n```')
 text=''.join(sections)
 # Existing notes point to local documentation; images remain relative to docs/.
 (ROOT/'docs/RK3576_STAGE5_ENGINEERING_MANUAL.md').write_text(text,encoding='utf-8',newline='\n')
 (local/'manual_source_manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('MANUAL_MARKDOWN',len(text.encode()),'bytes;',len(sources),'complete source blocks;',sum(x['lines'] for x in sources),'source lines; incomplete',a.allow_incomplete)
if __name__=='__main__':main()
