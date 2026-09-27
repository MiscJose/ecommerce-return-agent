type TableProps = {
    tableName: Record<string, any>[]
}

export function Table({tableName} : TableProps){
    return (
        tableName.length > 0 ? (
            <table>
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
                        <td key={key}>{value}</td>
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