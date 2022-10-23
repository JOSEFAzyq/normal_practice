package main

import (
	"context"
	"fmt"
	"time"
)

func main() {
	var (
		eventQueue     = make(chan interface{}, 100) //队列长度
		batchSize      = 4                           //批处理默认长度
		workers        = 2                           //处理协程数量
		lingerTime     = 1 * time.Second             //延时处理时间
		timeOutTime    = 2 * time.Second             //超时处理时间
		batchProcessor = func(valueCtx context.Context, batch []interface{}) error {
			//超时机制 2s未执行完成,则停止
			t := time.NewTimer(timeOutTime)
			processTime := make(chan string, 1)
			go func() {
				//fmt.Println("开始处理 batch handle start", batch, " ctx id:", valueCtx.Value("id"))

				// 假设每次处理3s
				time.Sleep(3 * time.Second)
				processTime <- fmt.Sprintln("处理完成 batch done", batch, " ctx id:", valueCtx.Value("id"))

			}()
			select {
			case res := <-processTime:
				fmt.Println(res)
				return nil
			case <-t.C:
				fmt.Println("handle 处理超时 time out", batch, "ctx id:", valueCtx.Value("id"))
				return nil
			}

			//c2 := make(chan string, 1)
			//t := time.NewTimer(2 * time.Second)
			//go func() {
			//	fmt.Println("开始处理 batch handle start", batch, " ctx id:", valueCtx.Value("id"))
			//	time.Sleep(3 * time.Second)
			//	c2 <- fmt.Sprintln("处理完成 batch done", batch, " ctx id:", valueCtx.Value("id"))
			//}()
			//select {
			//case res := <-c2:
			//	fmt.Println(res)
			//	return nil
			//case <-t.C:
			//	fmt.Println("handle 处理超时 time out", batch, "ctx id:", valueCtx.Value("id"))
			//	return nil
			//}
		}
		errHandler = func(err error, batch []interface{}) {
			fmt.Println("some error happens")
		}
	)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	for i := 0; i < workers; i++ {
		valueCtx := context.WithValue(ctx, "id", i)
		go func(ctx context.Context) {
			var batch []interface{}
			// 延时处理定时器,超过 lingerTime 还没有新消息进来则不等了,直接处理消息
			lingerTimer := time.NewTimer(lingerTime)
			// 时定时器需要在第一条消息进来后再开始计时(否则会在没消息时触发消息处理)
			// 这里初始化后直接停止,如果停止失败则等待定时器结束
			if !lingerTimer.Stop() {
				fmt.Println("定时器初始停止失败?")
				<-lingerTimer.C
			}
			// 进入循环消息处理
			//fmt.Println("worker 初始化", time.Now().Format("2006-01-02 15:04:05"), " ctx id:", valueCtx.Value("id"))
			for {
				select {
				case msg := <-eventQueue:
					//fmt.Println("收到消息 enter eventQueue", msg, " eventQueueLen:", len(eventQueue), " ctx id:", valueCtx.Value("id"))
					batch = append(batch, msg)

					if len(batch) != batchSize {
						if len(batch) == 1 {
							//fmt.Println("批量处理收到第一条消息,重置定时器 reset lingerTime", time.Now().Format("2006-01-02 15:04:05"), " ctx id:", valueCtx.Value("id"))
							lingerTimer.Reset(lingerTime)
						}
						//fmt.Println("批量处理容量未满,等待下一跳消息", " ctx id:", valueCtx.Value("id"))
						break
					}
					//fmt.Println("批量处理容量已满,开始处理消息 start batchP in eventQueue", batch, " ctx id:", valueCtx.Value("id"))

					if err := batchProcessor(ctx, batch); err != nil {
						errHandler(err, batch)
					}

					// 处理完后,停止定时器.防止定时器再次执行
					if !lingerTimer.Stop() {
						<-lingerTimer.C
					}

					batch = make([]interface{}, 0)
				case <-lingerTimer.C:
					//fmt.Println("定时器时间到", time.Now().Format("2006-01-02 15:04:05"), "开始处理消息 enter lingerTimer", batch, " ctx id:", valueCtx.Value("id"))
					if err := batchProcessor(ctx, batch); err != nil {
						errHandler(err, batch)
					}
					// 清空批处理容器
					batch = make([]interface{}, 0)
				}
			}
		}(valueCtx)
	}

	for i := 0; i < 10; i++ {
		//使用goroutine插入消息,保证主程不受影响
		time.Sleep(time.Millisecond)
		go func(i int) {
			eventQueue <- i
			fmt.Println("插入消息", i, time.Now().Format("2006-01-02 15:04:05"))
		}(i)
		time.Sleep(1 * time.Second / 2)
	}

	//假设主程执行了很久
	time.Sleep(6 * time.Second)

}
