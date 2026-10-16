import { useState, useEffect } from 'react'
import { Table } from './Table'
import { ChatPanel } from './ChatPanel';
import { getApiUrl } from './config';


async function fetchData() {
    const base_url = await getApiUrl()
    const response = await fetch(`${base_url}/admin/tables/`)

    if (!response.ok) {
      throw new Error(`Error: ${response.status}`)
    }

    const fetchedData = await response.json()
    return fetchedData
  
}

function App() {

  const [isBackendUp, setIsBackendUp] = useState(true)

  const [tables, setTables] = useState<Record<string, Record<string, any>[]>>({
    users: [],
    orders: [],
    order_items: [],
    returns: []
  });

  useEffect(() => {
    fetchData().then(data => setTables(data)).catch(error => setIsBackendUp(false))
  }, []);

  async function refreshTables(){
    const fetchedData = await fetchData()
    setTables(fetchedData)
  }
    
  return (
    <div className='bg-white min-h-screen'>
      <div>
        <h1 className='text-center text-2xl'>Welcome to the E-Commerce Return App!</h1>
      </div>

      {isBackendUp ?  
        (<div className='flex gap-2'>
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
        </div>) :
        (<div>
          <h1 className='py-2 text-center text-2xl text-green-600'>The demo backend is asleep. See the recording in the GitHub README.</h1>
        </div>)
      }
    </div>
  )
}

export default App
