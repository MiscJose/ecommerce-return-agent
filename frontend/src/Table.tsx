type TableProps = {
    tableName: Record<string, any>[]
}

export function Table({tableName} : TableProps){
    return (
        tableName.length > 0 ? (
            <table className="border-collapse border border-gray-400">
                <thead>
                    <tr>
                        {Object.keys(tableName[0]).map(col => 
                        <th key={col}>{col}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {tableName.map((record, index) =>
                    <tr key={index}>
                    {Object.entries(record).map(([key, value]) => 
                        <td key={key} className="border border-gray-300">{value}</td>
                    )}
                    </tr>
                    )}
                </tbody>
            </table>
            ) : (
            <p>Table Not Found!</p>
        )
    )
}