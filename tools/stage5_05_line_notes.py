"""Generate source-line learning notes tied to exact current file line numbers."""
from pathlib import Path
import hashlib,re
ROOT=Path(__file__).resolve().parents[1]
roles={
 'src/gui/backend_session.cpp':'Qt主线程中的QProcess适配，不加载模型；QObject context限制回调寿命，停止是向确认子PID发SIGINT',
 'src/gui/session_window.cpp':'Qt窗口只更新控件和读取有界结构化事件；关闭活动窗口先等待后台清理，重新开始创建新进程',
 'src/gui/main.cpp':'在QApplication及子线程之前建立StopSignals，校验隔离路径和参数，再进入Qt事件循环',
 'include/app/stop_signals.h':'沿用已验收sigwait普通线程，退出前join并恢复owner线程原信号mask',
 'include/gui/backend_session.h':'定义QProcess所有权、停止状态及QObject信号；值成员的析构顺序必须配合显式disconnect',
 'include/gui/session_window.h':'窗口拥有适配器及控件，任务诊断缓存有界，不持有AI回调内的借用Buffer'}
def explain(line):
 s=line.strip()
 code=re.sub(r'"(?:\\.|[^"\\])*"','""',s)
 if s.startswith('#include'):return '预处理阶段引入该实际声明；不创建对象、不启动线程。'
 if s.startswith('//'):return '该注释说明相邻代码的工程约束，本行不执行。'
 if s in {'{','}','};','});',');'}:return '结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。'
 if 'disconnect(' in s:return '断开指定QObject信号连接；本调用不注册新连接，防止成员析构阶段回调访问已销毁缓冲。'
 if 'connect(' in s:return '注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。'
 if 'Q_ASSERT' in s:return '调试断言要求GUI线程上下文；不是跨线程锁，也不替代发布构建的生命周期设计。'
 if 'QTimer::singleShot' in s:return '把动作推迟到事件循环执行，并提供QObject上下文，避免向已销毁窗口调用。'
 if 'kill(' in s:return '请求本对象持有且已确认的后台进程协作退出；调用返回不等于设备已经释放。'
 if 'sigtimedwait' in s:return '在普通信号接收线程限时等待被阻塞信号；此处不是异步signal handler。'
 if 'sigaddset' in s:return '把SIGINT或SIGTERM加入本线程将阻塞和同步等待的信号集合；不向任何进程发送信号。'
 if 'pthread_sigmask' in s:return '保存/设置调用线程信号mask，后续新线程继承；析构恢复owner线程原mask。'
 if '.join(' in s:return '等待所拥有线程真正结束，必须先发布停止条件；join前不能销毁线程借用对象。'
 if 'disconnect' in s:return '在成员销毁之前断开本对象回调，避免QProcess析构期间访问已销毁的缓冲。'
 if 'process_.start' in s:return '用独立程序路径与QStringList异步启动子进程，不拼接shell，不阻塞等待模型加载。'
 if '.read(' in s or 'readAllStandardOutput' in s:return '读取当前可用数据，保留未完整行片段；这不是对AI设备的阻塞推理调用。'
 if 'waitForFinished' in s:return '与阻塞等待有关的约束；正常GUI事件路径不使用这种等待。'
 if '.store(' in s or '.load(' in s:return '通过atomic读写线程间标志，避免普通bool数据竞争；对象寿命仍须由join保证。'
 if re.search(r'\bnew\s+[A-Za-z_]',code):return '构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。'
 if 'QJson' in s:return '按本行字段构造或解析JSON值；请求事件与会话结果具有不同schema，不从交错stdout猜业务文本。'
 if 'profilePartial_' in s or 'partial_' in s:return '维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。'
 if 'QIODevice::NewOnly' in s:return '要求文件不存在才创建，防止重复启动覆盖已有终端或验收结果。'
 if 'canonical' in s or 'startsWith' in s or 'report-root' in s:return '验证真实路径或隔离报告根边界，限制输出在授权目录；不会修改模型路径。'
 if 'setMaximumBlockCount' in s or 'tasks_.size()>64' in s:return '限制GUI保留的诊断/回答历史，完整业务证据另存文件，不静默删除任务本身。'
 if 'request_complete' in s:return '使用同Request ID的真实完成事件更新成功回答计数；自动测试只在规定完成数后停止。'
 if 'timestamp' in s or 'at_ns' in s:return '保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。'
 if 'duration(' in code or 'duration=' in code or '1e6' in code:return '用同一请求的时钟差换算毫秒；缺少任一端点显示未测量，不补零。'
 if 'screenshot' in s or 'grab()' in s:return '截取真实运行的当前QWidget并保存本次case，不合成运行画面。'
 if 'closeEvent' in s or 'event->ignore' in s:return '活动后台未退出时阻止窗口销毁，先协作停止；空闲状态才允许接受关闭。'
 if 'setEnabled' in s:return '根据活动状态启用或禁用控制项，防止运行中重复开始或改变当前会话参数。'
 if '.arg(' in s or 'setText(' in s:return '构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。'
 if 'throw ' in s or 'catch(' in s:return '将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。'
 if 'if(' in s or 'if (' in s:return '按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。'
 if 'for(' in s or 'for (' in s or 'while(' in s:return '遍历当前已有事件/控件或有限缓存；耗时模型循环仍在后台进程。'
 if 'return' in s:return '返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。'
 if s.startswith('signals:'):return 'Qt moc为信号生成元对象代码，signal发射不是后台模型工作线程。'
 if s.startswith(('public:','private:','private slots:')):return '指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。'
 if s.startswith(('class ','struct ','void ','bool ','int ','qint64 ','const ','auto ','QString','QFile','QTimer','QProcess','QLabel','QPushButton','QComboBox','QPlainTextEdit','std::')):return '声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。'
 return '执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。'
def main():
 out=['# 5.5 新增关键源码逐行学习索引\n\n本附录按最终真实文件行号定位，每条保留原句并给出语法提示；提示不是C++解析器或独立的完整业务语义证明，具体变量、条件和所有权需与前述人工状态机讲解及完整源码连读。完整文件见source_appendix，设计流程见statement_notes。生成器不会把说明插入生产源码。\n\n']
 for name,role in roles.items():
  p=ROOT/name;out.append('## '+name+'\n\n职责：'+role+'。SHA256：`'+hashlib.sha256(p.read_bytes()).hexdigest()+'`。\n\n')
  for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
   if not line.strip():continue
   out.append('行'+str(i)+' `'+line.strip().replace('`','\u0060')+'`：'+explain(line)+'\n\n')
 (ROOT/'docs/stage5_05_line_notes.md').write_text(''.join(out),encoding='utf-8');print('LINE_NOTES',len(''.join(out).encode()))
if __name__=='__main__':main()
