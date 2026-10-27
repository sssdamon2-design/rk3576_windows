"""Draw engineering diagrams from the audited current ownership/call relationships."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.font_manager import FontProperties
ROOT=Path(__file__).resolve().parents[1]
FONT=FontProperties(fname='C:/Windows/Fonts/simkai.ttf',size=13)

def setup(height):
 fig,ax=plt.subplots(figsize=(8,height),layout='constrained');ax.set_xlim(0,8);ax.set_ylim(0,height);ax.invert_yaxis();ax.axis('off');return fig,ax
def node(ax,x,y,w,h,text,color='#edf3f8'):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04',linewidth=1,edgecolor='#425466',facecolor=color))
 ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontproperties=FONT)
 return x+w/2,y+h/2,w,h
def arrow(ax,start,end):
 dx=end[0]-start[0];dy=end[1]-start[1]
 def distance(point):return min((point[2]/2+.045)/abs(dx) if dx else float('inf'),(point[3]/2+.045)/abs(dy) if dy else float('inf'))
 first=distance(start);last=distance(end)
 ax.annotate('',xy=(end[0]-dx*last,end[1]-dy*last),xytext=(start[0]+dx*first,start[1]+dy*first),arrowprops={'arrowstyle':'->','lw':1.2,'color':'#425466','shrinkA':0,'shrinkB':0})
def save(fig,out,name):fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)

def main():
 out=ROOT/'reports/stage5_05_local/plots';out.mkdir(exist_ok=True)
 fig,ax=setup(8.7)
 ui=node(ax,.3,.1,7.4,.75,'Qt主线程  控件和事件循环\nQProcess异步控制与JSONL观测','#dce9f4')
 main=node(ax,.3,1.2,7.4,.75,'原语音CLI子进程 main\n初始化  sigwait停止状态  汇总与清理')
 arrow(ax,ui,main)
 cam=node(ax,.3,2.5,3.05,.8,'Camera采集线程\nV4L2 MMAP DQBUF')
 frame=node(ax,.3,3.8,3.05,1,'一次NV12所有权复制\n三槽池 / latest共享帧\nQBUF后不借用驱动指针')
 capture=node(ax,4.1,2.5,3.6,.8,'采集与VAD线程\nHyperX / Silero')
 aq=node(ax,4.1,3.7,3.6,.65,'AudioBufferQueue 容量4')
 asr=node(ax,4.1,4.7,3.6,.8,'ASRWorker / SenseVoice\nRouter与在途额度≤2')
 inference=node(ax,3.65,5.9,4.05,1,'一个InferenceWorker FIFO\nQwen 或 RKNN加SmolVLM2\n等待容量2 / NPU调用串行')
 tts=node(ax,3.65,7.3,4.05,1,'TTSWorker 等待容量2\nKokoro合成后ALSA播放\nHyperX耳机 / drain')
 for a,b in [(cam,frame),(capture,aq),(aq,asr),(asr,inference),(frame,inference),(inference,tts)]:arrow(ax,a,b)
 ax.text(.3,6.2,'每个请求携带Request ID\n共享Ticket跨越推理和播放\n队列拒绝 / 到期 / 取消有终态\nGUI不加载模型或操作设备',fontproperties=FONT,va='top')
 save(fig,out,'system_architecture')
 fig,ax=setup(6.8)
 positions=[(.25,.15,3.35,.95,'驱动MMAP槽\nDQBUF后暂时可读'),(4.15,.15,3.6,.95,'应用空闲池\nunique_ptr独占槽'),(.25,1.65,3.35,.95,'复制NV12到自有Frame\n按stride / plane size处理'),(4.15,1.65,3.6,.95,'新shared_ptr控制块\n发布const帧 不保留可写别名'),(.25,3.15,3.35,.95,'QBUF立即归还驱动\n驱动可重新写入MMAP'),(4.15,3.15,3.6,.95,'latest与VLM共享持有\n当前帧不会被池覆盖'),(4.15,4.65,3.6,.95,'最后强引用释放\ndeleter归还活跃State'),(.25,4.65,3.35,.95,'池retire后最后归还\n释放payload与Frame对象')]
 points=[node(ax,*p) for p in positions]
 for a,b in [(0,2),(1,2),(2,3),(2,4),(3,5),(5,6),(6,7)]:arrow(ax,points[a],points[b])
 ax.plot([7.8,7.97,7.97],[points[6][1],points[6][1],points[1][1]],color='#425466',lw=1.2)
 ax.annotate('',xy=(7.8,points[1][1]),xytext=(7.97,points[1][1]),arrowprops={'arrowstyle':'->','color':'#425466','shrinkA':0,'shrinkB':0})
 ax.text(.3,6,'每次lease新建控制块，旧weak_ptr永久过期。\nRGB与Embedding按需复用；保留显式复制，不是零拷贝。',fontproperties=FONT)
 save(fig,out,'buffer_lifecycle')
 fig,ax=setup(6.8)
 labels=['普通sigwait线程收到信号\nGUI事件循环请求close','窗口仍有子进程则ignore\n发送协作SIGINT并保留对象','CLI停止采集和VAD\n关闭音频队列并唤醒等待','join ASRWorker\n销毁ASR recognizer','停止提交后处理推理队列\n排空或取消等待任务','join推理Worker\n销毁Qwen Runtime','排空或取消TTS等待任务\n活动同步合成与播放完成','join TTSWorker\n关闭ALSA并销毁Kokoro','停止Camera并销毁VLM\n输出完整Shutdown标记','子进程正常退出\nGUI finished后才关闭窗口']
 points=[]
 for i,label in enumerate(labels):
  col=0 if i<5 else 1;row=i%5;points.append(node(ax,.2+col*4,row*1.25+.15,3.6,.9,label))
 for i in range(9):
  if i!=4:arrow(ax,points[i],points[i+1])
  else:
   ax.plot([3.85,4,4],[points[4][1],points[4][1],points[5][1]],color='#425466',lw=1.2)
   ax.annotate('',xy=(4.15,points[5][1]),xytext=(4,points[5][1]),arrowprops={'arrowstyle':'->','color':'#425466','shrinkA':0,'shrinkB':0})
 save(fig,out,'shutdown_order')
 print('AUDITED_DIAGRAMS',out)
if __name__=='__main__':main()
