import { useState, useEffect } from "react";

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
            setMessages([{"content": fetchedResponse.question, "type": "ai", "additional_kwargs": {"channel": "customer"}}])
        }
        startConversation()
        }, []
    )

    return (
    
    <p>This is a placeholder</p>
    
    )
}