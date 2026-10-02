import { useState, useEffect, type ChangeEvent, type FormEvent } from "react";

export function ChatPanel(){
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
            setThreadID(fetchedData.threadID)
            setMessages(fetchedData.result.messages)
            setIsComplete(true)

        }
        else {
            setThreadID(fetchedData.thread_id)
            const new_message = [{"content": fetchedData.result['__interrupt__'][0].value["question"], "type": "ai", "additional_kwargs": fetchedData.result['__interrupt__'][0].value["additional_kwargs"]}]
            setMessages([...fetchedData.result.messages, ...new_message])
        }

        setInputValue('')
    }
        
    return (

        <>
            {isComplete ? (
            <p>Thank you!</p>
            ) : (
            <form onSubmit={handleFormSubmit} action="">
                <input onChange={handleInputChange} value={inputValue} type="text" />
                <button>Submit</button>
            </form>
            )}

            <div>
                <ul>
                    {manager_channel_messages.map((message, index) =>
                        <li key={index}>{message.content}</li>
                    )}
                </ul>
            </div>

            <div>
                <ul>
                    {customer_channel_messages.map((message, index) =>
                        <li key={index}>{message.content}</li>
                    )}
                </ul>
            </div>
        </>

    )
}