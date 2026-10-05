import { useState, useEffect } from 'react'
import { Table } from './Table'
import { ChatPanel } from './ChatPanel';

function App() {
  
  const [tables, setTables] = useState<Record<string, Record<string, any>[]>>({
    users: [],
    orders: [],
    order_items: [],
    returns: []
  });

  async function refreshTables(){
    const response = await fetch("http://localhost:8000/admin/tables/")
    const fetchedData = await response.json()
    setTables({"users": fetchedData['users'],"orders": fetchedData['orders'],"order_items": fetchedData['order_items'],"returns": fetchedData['returns']})
  }

  useEffect(() => {
    refreshTables()
  }, []);
    
  return (
    <div className='bg-white min-h-screen gap-4'>
      <div id="center">
        <h1 className='text-center text-2xl'>Welcome to the App!</h1>
      </div>

      <div id='demo' className='flex gap-2'>
        <section id='chat-panel' className='flex-1'>
          <ChatPanel onReturnFinalized={refreshTables} />
        </section>
        <section id='tables-panel' className='flex-1 overflow-x-auto'>
          <div className='my-2'>
            <Table name='Users' rows={tables.users} />
          </div>
          <div className='my-2'>
            <Table name='Orders' rows={tables.orders} />
          </div>
          <div className='my-2'>
            <Table name='Order Items' rows={tables.order_items} />
          </div>
          <div className='my-2'>
            <Table name='Returns' rows={tables.returns} />
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
