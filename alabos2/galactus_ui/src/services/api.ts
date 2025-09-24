import axios, { AxiosInstance, AxiosResponse } from 'axios'
import {
  TaskTemplateCreate,
  TaskTemplateResponse,
  WorkflowCreate,
  WorkflowResponse,
  JobCreate,
  JobResponse,
  TaskResponse,
  SampleResponse,
  SampleCreate,
} from '@/types/api'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          
          localStorage.removeItem('auth_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  
  async getTaskTemplates(params?: {
    category?: string
    status?: string
    skip?: number
    limit?: number
  }): Promise<TaskTemplateResponse[]> {
    const response: AxiosResponse<TaskTemplateResponse[]> = await this.client.get('/task-templates/', { params })
    return response.data
  }

  async getTaskTemplate(id: string): Promise<TaskTemplateResponse> {
    const response: AxiosResponse<TaskTemplateResponse> = await this.client.get(`/task-templates/${id}`)
    return response.data
  }

  async createTaskTemplate(data: TaskTemplateCreate): Promise<TaskTemplateResponse> {
    console.log(data)
    const response: AxiosResponse<TaskTemplateResponse> = await this.client.post('/task-templates/', data)
    return response.data
  }

  async updateTaskTemplate(id: string, data: TaskTemplateCreate): Promise<TaskTemplateResponse> {
    const response: AxiosResponse<TaskTemplateResponse> = await this.client.put(`/task-templates/${id}`, data)
    return response.data
  }

  async deleteTaskTemplate(id: string): Promise<void> {
    await this.client.delete(`/task-templates/${id}`)
  }

  async validateTaskTemplate(id: string, inputs: Record<string, any>): Promise<any> {
    const response = await this.client.post(`/task-templates/${id}/validate`, inputs)
    return response.data
  }

  
  async getWorkflows(params?: {
    status?: string
    skip?: number
    limit?: number
  }): Promise<WorkflowResponse[]> {
    const response: AxiosResponse<WorkflowResponse[]> = await this.client.get('/workflows/', { params })
    return response.data
  }

  async getWorkflow(id: string): Promise<WorkflowResponse> {
    const response: AxiosResponse<WorkflowResponse> = await this.client.get(`/workflows/${id}`)
    return response.data
  }

  async createWorkflow(data: WorkflowCreate): Promise<WorkflowResponse> {
    const response: AxiosResponse<WorkflowResponse> = await this.client.post('/workflows/', data)
    return response.data
  }

  async updateWorkflowStatus(id: string, status: string): Promise<any> {
    const response = await this.client.put(`/workflows/${id}/status`, null, {
      params: { status }
    })
    return response.data
  }

  async getWorkflowSamples(id: string): Promise<SampleResponse[]> {
    const response: AxiosResponse<SampleResponse[]> = await this.client.get(`/workflows/${id}/samples`)
    return response.data
  }

  async createWorkflowSample(workflowId: string, data: SampleCreate): Promise<SampleResponse> {
    const response: AxiosResponse<SampleResponse> = await this.client.post(`/workflows/${workflowId}/samples`, data)
    return response.data
  }

  async optimizeWorkflow(id: string, targets?: Record<string, any>): Promise<any> {
    const response = await this.client.post(`/workflows/${id}/optimize`, { optimization_targets: targets })
    return response.data
  }

  
  async getJobs(params?: {
    status?: string
    priority?: number
    skip?: number
    limit?: number
  }): Promise<JobResponse[]> {
    const response: AxiosResponse<JobResponse[]> = await this.client.get('/jobs/', { params })
    return response.data
  }

  async getJob(id: string): Promise<JobResponse> {
    const response: AxiosResponse<JobResponse> = await this.client.get(`/jobs/${id}`)
    return response.data
  }

  async createJob(data: JobCreate): Promise<JobResponse> {
    const response: AxiosResponse<JobResponse> = await this.client.post('/jobs/', data)
    return response.data
  }

  async updateJobStatus(id: string, status: string): Promise<any> {
    const response = await this.client.put(`/jobs/${id}/status`, null, {
      params: { status }
    })
    return response.data
  }

  async queueJob(id: string): Promise<any> {
    const response = await this.client.post(`/jobs/${id}/queue`)
    return response.data
  }

  async cancelJob(id: string): Promise<any> {
    const response = await this.client.post(`/jobs/${id}/cancel`)
    return response.data
  }

  async getJobQueueStatus(id: string): Promise<any> {
    const response = await this.client.get(`/jobs/${id}/queue`)
    return response.data
  }

  async getQueueStatus(): Promise<any> {
    const response = await this.client.get('/jobs/queue/status')
    return response.data
  }

  
  async getTasks(params?: {
    status?: string
    job_id?: string
    workflow_id?: string
    skip?: number
    limit?: number
  }): Promise<TaskResponse[]> {
    const response: AxiosResponse<TaskResponse[]> = await this.client.get('/tasks/', { params })
    return response.data
  }

  async getTask(id: string): Promise<TaskResponse> {
    const response: AxiosResponse<TaskResponse> = await this.client.get(`/tasks/${id}`)
    return response.data
  }

  async cancelTask(id: string): Promise<any> {
    const response = await this.client.post(`/tasks/${id}/cancel`)
    return response.data
  }

  
  async healthCheck(): Promise<any> {
    const response = await this.client.get('/health')
    return response.data
  }
}

export const apiClient = new ApiClient()
