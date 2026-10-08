import { useState, useEffect, type ChangeEvent, type FormEvent } from "react";

type ChatPanelProps = {
    onReturnFinalized: () => void
}


export function ChatPanel({onReturnFinalized} : ChatPanelProps){
    const [threadID, setThreadID] = useState <string | null>(null)
    const [messages, setMessages] = useState <Record<string, any>[]>([])
    const [inputValue, setInputValue] = useState <string>('')
    const [isComplete, setIsComplete] = useState <boolean>(false)

    useEffect(() => {
        async function startConversation(){
            const response = await fetch('http://localhost:8000/returns/start', {method:'post'})
            const fetchedResponse = await response.json()
            setThreadID(fetchedResponse['thread_id'])
            setMessages([{"content": fetchedResponse.question, "type": "ai", "additional_kwargs": fetchedResponse.additional_kwargs}])
        }
        startConversation()
        }, []
    )


    let latest_message = messages[messages.length - 1]
    let active_channel = null

    if (latest_message==null){
        active_channel = "customer"
    }
    else {
        active_channel = latest_message.additional_kwargs.channel
    }

    let manager_channel_messages = messages.filter(message => message.additional_kwargs.channel === "manager")
    let customer_channel_messages = messages.filter(message => message.additional_kwargs.channel === "customer")

    function handleInputChange(e : ChangeEvent <HTMLInputElement>){
        setInputValue(e.target.value)
    }

   async function handleFormSubmit(e : FormEvent <HTMLFormElement>){
        e.preventDefault()
        const body = {"thread_id": threadID, "customer_answer": inputValue}
        const response = await fetch('http://localhost:8000/returns/resume', {
            method: "post", 
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        }) 
        
        const fetchedData = await response.json()

        if (!fetchedData.result.__interrupt__ ){
            setThreadID(fetchedData.thread_id)
            setMessages(fetchedData.result.messages)
            setIsComplete(true)

            onReturnFinalized()

        }
        else {
            setThreadID(fetchedData.thread_id)
            const new_message = [{"content": fetchedData.result['__interrupt__'][0].value["question"], "type": "ai", "additional_kwargs": fetchedData.result['__interrupt__'][0].value["additional_kwargs"]}]
            setMessages([...fetchedData.result.messages, ...new_message])
        }

        setInputValue('')
    }

        
    return (

        <div className="max-w-3/5 mx-auto">
            <div className="py-4">
                <h2 className="text-xl py-2">Manager Chat</h2>
                <ul className="flex flex-col gap-2 px-4 py-4 h-50 bg-slate-800">
                    {manager_channel_messages.map((message, index) =>
                        <li className={
                            `rounded-xl p-1 max-w-4/6 ${message.type == 'ai' ? 
                                'self-start bg-orange-400' :
                                ' self-end bg-green-400'} 
                            `} key={index}>{message.content}</li>
                    )}
                </ul>
            </div>

            <div className="py-4">
                <h2 className="text-xl py-2">Customer Chat</h2>
                <ul className="flex flex-col gap-2 px-4 py-4 h-70 bg-slate-800">
                    {customer_channel_messages.map((message, index) =>
                        <li className={
                            `rounded-xl p-1 max-w-4/6 ${message.type == 'ai' ? 
                                'self-start bg-orange-400' :
                                'self-end bg-blue-400'} 
                            `} key={index}>{message.content}</li>
                    )}
                </ul>
            </div>

                        {isComplete ? (
            <p className="text-red-600 text-xl py-6">Thank you for using this demo!</p>
            ) : (

            <div className="flex justify-end px-2 py-4 bg-slate-800">
                <form className="flex gap-2" onSubmit={handleFormSubmit}>
                    <input className="bg-white" onChange={handleInputChange} value={inputValue} type="text" />
                    <button className="bg-white px-1 rounded-lg hover:bg-blue-400">Submit</button>
                </form>
            </div>
            )}
        </div>

    )
}