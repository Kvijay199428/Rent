import { Routes, Route } from 'react-router-dom'
import TenantPortal from '../pages/TenantPortal'

function App() {
    return (
        <Routes>
            <Route path=":token" element={<TenantPortal />} />
            <Route path="*" element={<div className="p-8 text-center">Invalid URL</div>} />
        </Routes>
    )
}

export default App
