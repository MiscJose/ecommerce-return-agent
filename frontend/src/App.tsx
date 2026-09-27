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

  useEffect(() => {
    async function getData(){
      const response = await fetch("http://localhost:8000/admin/tables/")
      const fetchedData = await response.json()
      setTables({"users": fetchedData['users'],"orders": fetchedData['orders'],"order_items": fetchedData['order_items'],"returns": fetchedData['returns']})
    }
    getData()
  }, []);
  

  console.log(tables)
  
  return (
    <>
      <section id="center">
        <p>Welcome to the App!</p>
      </section>

      <div id='demo'>
        <section id='chat-panel'>
          <p>Placeholder for Chat!</p>
        </section>
        <section id='tables-panel'>
          <Table tableName={tables.users} />
          <Table tableName={tables.orders} />
          <Table tableName={tables.order_items} />
          <Table tableName={tables.returns} />
        </section>
      </div>

      
    </>
  )
}

export default App
