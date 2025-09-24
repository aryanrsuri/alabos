import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { HomePage } from '@/pages/HomePage'
import { TaskTemplatesPage } from '@/pages/TaskTemplatesPage'
import { TaskTemplateBuilderPage } from '@/pages/TaskTemplateBuilderPage'
import { WorkflowsPage } from '@/pages/WorkflowsPage'
import { WorkflowDesignerPage } from '@/pages/WorkflowDesignerPage'
import { JobsPage } from '@/pages/JobsPage'
import { DevicesPage } from '@/pages/DevicesPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/task-templates" element={<TaskTemplatesPage />} />
          <Route path="/task-templates/new" element={<TaskTemplateBuilderPage />} />
          <Route path="/task-templates/:id" element={<TaskTemplateBuilderPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/workflows/new" element={<WorkflowDesignerPage />} />
          <Route path="/workflows/:id" element={<WorkflowDesignerPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/devices" element={<DevicesPage />} />
        </Routes>
      </Layout>
    </div>
  )
}

export default App
