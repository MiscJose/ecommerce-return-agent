import { useState, useEffect } from 'react'
import { Table } from './Table'
import { ChatPanel } from './ChatPanel';
import './App.css'


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
    <div className='bg-white'>
      <div id="center">
        <h1 className='text-gray-900'>Welcome to the App!</h1>
        <h2 className='text-gray-500'>This is a returns ecommerce simulation</h2>
      </div>

      <div id='demo'>
        <section id='chat-panel'>
          <ChatPanel onReturnFinalized={refreshTables} />
        </section>
        <section id='tables-panel'>
          <Table tableName={tables.users} />
          <Table tableName={tables.orders} />
          <Table tableName={tables.order_items} />
          <Table tableName={tables.returns} />
        </section>
      </div>
    </div>
  )
}

export default App
