import { useState, useEffect } from 'react'
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

      <section>
        {tables.users.length > 0 ? 
          (<table>
            <thead>
              <tr>
                  {Object.keys(tables.users['0']).map(col => 
                    <th key={col}>{col}</th>)}
              </tr>
            </thead>
            <tbody>
              {tables.users.map(user =>
                <tr key={user.user_id}>
                {Object.entries(user).map(([key, value]) => 
                  <td key={key}>{value}</td>
                )}
                </tr>
               )}
            </tbody>
          </table>
          ) : (
            <p>Table Not Found!</p>
          )
        }
      </section>
    </>
  )
}

export default App
