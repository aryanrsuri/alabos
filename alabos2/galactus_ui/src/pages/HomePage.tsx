import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileText, GitBranch, Play, Activity, Plus } from 'lucide-react'
import { apiClient } from '@/services/api'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export function HomePage() {
  const { data: workflows, isLoading: workflowsLoading } = useQuery({
    queryKey: ['workflows', 'recent'],
    queryFn: () => apiClient.getWorkflows({ limit: 5 }),
  })

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs', 'recent'],
    queryFn: () => apiClient.getJobs({ limit: 5 }),
  })

  const { data: taskTemplates, isLoading: templatesLoading } = useQuery({
    queryKey: ['task-templates', 'recent'],
    queryFn: () => apiClient.getTaskTemplates({ limit: 5 }),
  })

  const { data: queueStatus } = useQuery({
    queryKey: ['queue-status'],
    queryFn: () => apiClient.getQueueStatus(),
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  const stats = [
    {
      name: 'Active Workflows',
      value: workflows?.filter(w => w.status === 'active' || w.status === 'running').length || 0,
      icon: GitBranch,
      href: '/workflows',
    },
    {
      name: 'Running Jobs',
      value: jobs?.filter(j => j.status === 'running').length || 0,
      icon: Play,
      href: '/jobs',
    },
    {
      name: 'Task Templates',
      value: taskTemplates?.length || 0,
      icon: FileText,
      href: '/task-templates',
    },
    {
      name: 'Queue Position',
      value: queueStatus?.total_queued || 0,
      icon: Activity,
      href: '/jobs',
    },
  ]

  return (
    <div className="space-y-6">
      
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Monitor your laboratory operations and manage workflows
          </p>
        </div>
        <div className="flex space-x-3">
          <Button asChild>
            <Link to="/task-templates/new">
              <Plus className="mr-2 h-4 w-4" />
              New Template
            </Link>
          </Button>
          <Button asChild>
            <Link to="/workflows/new">
              <Plus className="mr-2 h-4 w-4" />
              New Workflow
            </Link>
          </Button>
        </div>
      </div>

      
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name} className="px-4 py-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <stat.icon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    {stat.name}
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {stat.value}
                  </dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <Link
                to={stat.href}
                className="text-sm font-medium text-primary-600 hover:text-primary-500"
              >
                View all
              </Link>
            </div>
          </Card>
        ))}
      </div>

      
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        
        <Card>
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Workflows</h3>
            {workflowsLoading ? (
              <div className="animate-pulse space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-12 bg-gray-200 rounded"></div>
                ))}
              </div>
            ) : workflows && workflows.length > 0 ? (
              <div className="space-y-3">
                {workflows.slice(0, 5).map((workflow) => (
                  <div key={workflow.id} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{workflow.name}</p>
                      <p className="text-sm text-gray-500 capitalize">{workflow.status}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">
                        {workflow.sample_count} samples
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(workflow.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No workflows yet</p>
            )}
            <div className="mt-4">
              <Link
                to="/workflows"
                className="text-sm font-medium text-primary-600 hover:text-primary-500"
              >
                View all workflows
              </Link>
            </div>
          </div>
        </Card>

        
        <Card>
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Jobs</h3>
            {jobsLoading ? (
              <div className="animate-pulse space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-12 bg-gray-200 rounded"></div>
                ))}
              </div>
            ) : jobs && jobs.length > 0 ? (
              <div className="space-y-3">
                {jobs.slice(0, 5).map((job) => (
                  <div key={job.id} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{job.name}</p>
                      <p className="text-sm text-gray-500 capitalize">{job.status}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Priority {job.priority}</p>
                      <p className="text-xs text-gray-400">
                        {new Date(job.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No jobs yet</p>
            )}
            <div className="mt-4">
              <Link
                to="/jobs"
                className="text-sm font-medium text-primary-600 hover:text-primary-500"
              >
                View all jobs
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
