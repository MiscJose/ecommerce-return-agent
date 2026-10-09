type TableProps = {
    name: string
    rows: Record<string, any>[]
}

export function Table({name, rows} : TableProps){
    return (
        rows.length > 0 ? (
            <div>
                <h2 className="text-xl my-2">{name}</h2>
                <table className="text-md border border-separate text-center">
                    <thead>
                        <tr>
                            {Object.keys(rows[0]).map(col => 
                            <th key={col} className="border bg-slate-600 text-white p-1">{col}</th>)}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((record, index) =>
                        <tr key={index}>
                        {Object.entries(record).map(([key, value]) => 
                            <td key={key} className="border p-1">{String(value)}</td>
                        )}
                        </tr>
                        )}
                    </tbody>
                </table>
            </div>
            ) : (
            <h2> {name} Table Not Found!</h2>
        )
    )
}