import { useState, useEffect } from 'react'
import './App.css'



function App() {

  const [tables, setTables] = useState({"users": [], "orders": [], "order_items": [], "returns": []})

  function updateTables() {
    useEffect(() => {
      async function getData(){
        const response = await fetch("http://localhost:8000/admin/tables/")
        const fetchedData = await response.json()
        setTables({"users": fetchedData['users'],"orders": fetchedData['orders'],"order_items": fetchedData['order_items'],"returns": fetchedData['returns']})
      }
      getData
    });
  }

  console.log(tables)
  
  return (
    <>
      <section id="center">
        <p>Welcome to the App!</p>
      </section>
    </>
  )
}

export default App
