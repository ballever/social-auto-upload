<template>
  <div class="one-click-publish">
    <div class="page-header">
      <h2>一键多平台发布</h2>
      <p class="subtitle">输入一份内容，同时发布到多个平台的多个账号</p>
    </div>

    <!-- 平台选择 -->
    <div class="section">
      <h3>选择平台 <span class="required">*</span></h3>
      <el-checkbox-group v-model="selectedPlatforms" class="platform-checkboxes">
        <el-checkbox 
          v-for="platform in platforms" 
          :key="platform.key"
          :label="platform.key"
          class="platform-checkbox"
        >
          {{ platform.name }}
        </el-checkbox>
      </el-checkbox-group>
    </div>

    <!-- 账号选择（按平台分组） -->
    <div class="section" v-if="selectedPlatforms.length > 0">
      <h3>选择账号 <span class="required">*</span></h3>
      <div v-for="platformKey in selectedPlatforms" :key="platformKey" class="account-group">
        <h4>{{ getPlatformName(platformKey) }}</h4>
        <el-checkbox-group v-model="selectedAccounts[platformKey]" class="account-checkboxes">
          <el-checkbox 
            v-for="account in getAccountsByPlatform(platformKey)" 
            :key="account.id"
            :label="account.id"
          >
            {{ account.name }}
          </el-checkbox>
        </el-checkbox-group>
        <div v-if="getAccountsByPlatform(platformKey).length === 0" class="no-account">
          暂无可用账号，请先在账号管理中添加
        </div>
      </div>
    </div>

    <!-- 视频上传区域 -->
    <div class="section">
      <h3>视频 <span class="required">*</span></h3>
      <div class="upload-options">
        <el-button type="primary" @click="showUploadOptions" class="upload-btn">
          <el-icon><Upload /></el-icon>
          上传视频
        </el-button>
      </div>
      
      <!-- 已上传文件列表 -->
      <div v-if="fileList.length > 0" class="uploaded-files">
        <div v-for="(file, index) in fileList" :key="index" class="file-item">
          <el-link :href="file.url" target="_blank" type="primary">{{ file.name }}</el-link>
          <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(2) }}MB</span>
          <el-button type="danger" size="small" @click="removeFile(index)">删除</el-button>
        </div>
      </div>
    </div>

    <!-- 上传选项弹窗 -->
    <el-dialog v-model="uploadOptionsVisible" title="选择上传方式" width="400px">
      <div class="upload-options-content">
        <el-button type="primary" @click="selectLocalUpload" class="option-btn">
          <el-icon><Upload /></el-icon>
          本地上传
        </el-button>
        <el-button type="success" @click="selectMaterialLibrary" class="option-btn">
          <el-icon><Folder /></el-icon>
          素材库
        </el-button>
      </div>
    </el-dialog>

    <!-- 本地上传弹窗 -->
    <el-dialog v-model="localUploadVisible" title="本地上传" width="600px">
      <el-upload
        class="video-upload"
        drag
        :auto-upload="true"
        :action="`${apiBaseUrl}/upload`"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        multiple
        accept="video/*"
        :headers="authHeaders"
      >
        <el-icon class="el-icon--upload"><Upload /></el-icon>
        <div class="el-upload__text">
          将视频文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">支持MP4、AVI等视频格式</div>
        </template>
      </el-upload>
    </el-dialog>

    <!-- 素材库选择弹窗 -->
    <el-dialog v-model="materialLibraryVisible" title="选择素材" width="800px">
      <div class="material-library-content">
        <el-checkbox-group v-model="selectedMaterials">
          <div class="material-list">
            <div v-for="material in materials" :key="material.id" class="material-item">
              <el-checkbox :label="material.id" class="material-checkbox">
                <div class="material-info">
                  <div class="material-name">{{ material.filename }}</div>
                  <div class="material-details">
                    <span class="file-size">{{ material.filesize }}MB</span>
                    <span class="upload-time">{{ material.upload_time }}</span>
                  </div>
                </div>
              </el-checkbox>
            </div>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="materialLibraryVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMaterialSelection">确定</el-button>
      </template>
    </el-dialog>

    <!-- 封面图片上传 -->
    <div class="section">
      <h3>封面图片 <span class="optional">(可选)</span></h3>
      <el-upload
        class="cover-uploader"
        :action="`${apiBaseUrl}/upload`"
        :show-file-list="false"
        :on-success="handleCoverUploadSuccess"
        :on-error="handleCoverUploadError"
        :before-upload="beforeCoverUpload"
        accept="image/*"
        :headers="authHeaders"
      >
        <div v-if="coverImage" class="cover-preview">
          <img :src="coverImage.url" class="cover-image" />
          <div class="cover-actions">
            <el-button type="primary" size="small" @click.stop="changeCoverImage">更换</el-button>
            <el-button type="danger" size="small" @click.stop="removeCoverImage">删除</el-button>
          </div>
        </div>
        <el-button v-else type="primary" plain>
          <el-icon><Picture /></el-icon>
          上传封面图片
        </el-button>
      </el-upload>
    </div>

    <!-- 标题 -->
    <div class="section">
      <h3>标题 <span class="required">*</span></h3>
      <el-input
        v-model="title"
        type="textarea"
        :rows="3"
        placeholder="请输入标题"
        maxlength="100"
        show-word-limit
        class="title-input"
      />
    </div>

    <!-- 简介 -->
    <div class="section">
      <h3>简介 <span class="optional">(可选)</span></h3>
      <el-input
        v-model="description"
        type="textarea"
        :rows="4"
        placeholder="请输入作品简介"
        maxlength="500"
        show-word-limit
        class="description-input"
      />
    </div>

    <!-- 话题 -->
    <div class="section">
      <h3>话题</h3>
      <div class="topic-display">
        <div class="selected-topics">
          <el-tag
            v-for="(topic, index) in selectedTopics"
            :key="index"
            closable
            @close="removeTopic(index)"
            class="topic-tag"
          >
            #{{ topic }}
          </el-tag>
        </div>
        <el-button type="primary" plain @click="topicDialogVisible = true">添加话题</el-button>
      </div>
    </div>

    <!-- 添加话题弹窗 -->
    <el-dialog v-model="topicDialogVisible" title="添加话题" width="600px">
      <div class="topic-dialog-content">
        <div class="custom-topic-input">
          <el-input v-model="customTopic" placeholder="输入自定义话题" class="custom-input">
            <template #prepend>#</template>
          </el-input>
          <el-button type="primary" @click="addCustomTopic">添加</el-button>
        </div>
        <div class="recommended-topics">
          <h4>推荐话题</h4>
          <div class="topic-grid">
            <el-button
              v-for="topic in recommendedTopics"
              :key="topic"
              :type="selectedTopics.includes(topic) ? 'primary' : 'default'"
              @click="toggleRecommendedTopic(topic)"
              class="topic-btn"
            >
              {{ topic }}
            </el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="topicDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="topicDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>

    <!-- 原创声明 -->
    <div class="section">
      <el-checkbox v-model="isOriginal" label="声明原创" />
    </div>

    <!-- 定时发布 -->
    <div class="section">
      <h3>定时发布</h3>
      <div class="schedule-controls">
        <el-switch v-model="scheduleEnabled" active-text="定时发布" inactive-text="立即发布" />
        <div v-if="scheduleEnabled" class="schedule-settings">
          <div class="schedule-item">
            <span class="label">每天发布视频数：</span>
            <el-select v-model="videosPerDay" placeholder="选择发布数量">
              <el-option v-for="num in 55" :key="num" :label="num" :value="num" />
            </el-select>
          </div>
          <div class="schedule-item">
            <span class="label">每天发布时间：</span>
            <el-time-select
              v-for="(time, index) in dailyTimes"
              :key="index"
              v-model="dailyTimes[index]"
              start="00:00"
              step="00:30"
              end="23:30"
              placeholder="选择时间"
            />
            <el-button
              v-if="dailyTimes.length < videosPerDay"
              type="primary"
              size="small"
              @click="dailyTimes.push('10:00')"
            >
              添加时间
            </el-button>
          </div>
          <div class="schedule-item">
            <span class="label">开始天数：</span>
            <el-select v-model="startDays" placeholder="选择开始天数">
              <el-option label="明天" :value="0" />
              <el-option label="后天" :value="1" />
            </el-select>
          </div>
        </div>
      </div>
    </div>

    <!-- 发布按钮 -->
    <div class="action-buttons">
      <el-button @click="resetForm">重置</el-button>
      <el-button
        type="primary"
        @click="handlePublish"
        :loading="publishing"
        :disabled="!canPublish"
        size="large"
      >
        一键发布到 {{ totalTaskCount }} 个账号
      </el-button>
    </div>

    <!-- 发布进度对话框 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="发布进度"
      width="600px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="publishProgress === 100"
    >
      <div class="publish-progress">
        <el-progress 
          :percentage="publishProgress" 
          :status="publishProgress === 100 ? 'success' : ''"
        />
        <div class="publish-results" v-if="publishResults.length > 0">
          <div 
            v-for="(result, index) in publishResults" 
            :key="index"
            :class="['result-item', result.status]"
          >
            <el-icon v-if="result.status === 'success'"><Check /></el-icon>
            <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
            <el-icon v-else><Loading /></el-icon>
            <span class="platform-account">{{ result.platform }} - {{ result.account }}</span>
            <span class="message">{{ result.message }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Upload, Folder, Picture, Check, Close, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { materialApi } from '@/api/material'
import { http } from '@/utils/request'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

const authHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

const accountStore = useAccountStore()
const appStore = useAppStore()

// 平台列表
const platforms = [
  { key: 3, name: '抖音' },
  { key: 4, name: '快手' },
  { key: 2, name: '视频号' },
  { key: 1, name: '小红书' },
  { key: 5, name: 'Bilibili' },
  { key: 6, name: '百家号' }
]

const platformNameMap = {
  1: '小红书', 2: '视频号', 3: '抖音', 4: '快手', 5: 'Bilibili', 6: '百家号'
}

// 选中的平台
const selectedPlatforms = ref([])
// 选中的账号（按平台分组）
const selectedAccounts = reactive({})

// 监听平台选择变化
watch(selectedPlatforms, (newPlatforms) => {
  newPlatforms.forEach(key => {
    if (!selectedAccounts[key]) {
      selectedAccounts[key] = []
    }
  })
  Object.keys(selectedAccounts).forEach(key => {
    if (!newPlatforms.includes(parseInt(key))) {
      selectedAccounts[key] = []
    }
  })
}, { deep: true })

// 表单数据
const fileList = ref([])
const coverImage = ref(null)
const title = ref('')
const description = ref('')
const selectedTopics = ref([])
const scheduleEnabled = ref(false)
const videosPerDay = ref(1)
const dailyTimes = ref(['10:00'])
const startDays = ref(0)
const isOriginal = ref(false)

// 上传相关
const uploadOptionsVisible = ref(false)
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)

// 话题相关
const topicDialogVisible = ref(false)
const customTopic = ref('')
const recommendedTopics = [
  '游戏', '电影', '音乐', '美食', '旅行', '文化',
  '科技', '生活', '娱乐', '体育', '教育', '艺术',
  '健康', '时尚', '美妆', '摄影', '宠物', '汽车'
]

// 发布状态
const publishing = ref(false)
const progressDialogVisible = ref(false)
const publishProgress = ref(0)
const publishResults = ref([])

// 方法
const getPlatformName = (key) => platformNameMap[key] || '未知平台'

const getAccountsByPlatform = (platformKey) => {
  const platformName = platformNameMap[platformKey]
  return accountStore.accounts.filter(acc => acc.platform === platformName)
}

const totalTaskCount = computed(() => {
  let count = 0
  selectedPlatforms.value.forEach(platformKey => {
    count += (selectedAccounts[platformKey] || []).length
  })
  return count
})

const canPublish = computed(() => {
  return totalTaskCount.value > 0 && fileList.value.length > 0 && title.value.trim()
})

// 上传相关方法
const showUploadOptions = () => {
  uploadOptionsVisible.value = true
}

const selectLocalUpload = () => {
  uploadOptionsVisible.value = false
  localUploadVisible.value = true
}

const selectMaterialLibrary = async () => {
  uploadOptionsVisible.value = false
  if (materials.value.length === 0) {
    try {
      const response = await materialApi.getAllMaterials()
      if (response.code === 200) {
        appStore.setMaterials(response.data)
      }
    } catch (error) {
      console.error('获取素材列表出错:', error)
    }
  }
  selectedMaterials.value = []
  materialLibraryVisible.value = true
}

const confirmMaterialSelection = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('请选择至少一个素材')
    return
  }
  selectedMaterials.value.forEach(materialId => {
    const material = materials.value.find(m => m.id === materialId)
    if (material) {
      const fileInfo = {
        name: material.filename,
        url: materialApi.getMaterialPreviewUrl(material.file_path.split('/').pop()),
        path: material.file_path,
        size: material.filesize * 1024 * 1024,
        type: 'video/mp4'
      }
      const exists = fileList.value.some(file => file.path === fileInfo.path)
      if (!exists) {
        fileList.value.push(fileInfo)
      }
    }
  })
  materialLibraryVisible.value = false
  selectedMaterials.value = []
  ElMessage.success('素材添加成功')
}

const handleUploadSuccess = (response, file) => {
  if (response.code === 200) {
    const filePath = response.data.path || response.data
    const filename = filePath.split('/').pop()
    fileList.value.push({
      name: file.name,
      url: materialApi.getMaterialPreviewUrl(filename),
      path: filePath,
      size: file.size,
      type: file.type
    })
    ElMessage.success('文件上传成功')
  } else {
    ElMessage.error(response.msg || '上传失败')
  }
}

const handleUploadError = () => {
  ElMessage.error('文件上传失败')
}

const removeFile = (index) => {
  fileList.value.splice(index, 1)
  ElMessage.success('文件删除成功')
}

// 封面图片相关
const beforeCoverUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isImage) { ElMessage.error('只能上传图片文件！'); return false }
  if (!isLt5M) { ElMessage.error('图片大小不能超过5MB！'); return false }
  return true
}

const handleCoverUploadSuccess = (response, file) => {
  if (response.code === 200) {
    const filePath = response.data.path || response.data
    const filename = filePath.split('/').pop()
    coverImage.value = {
      name: file.name,
      url: materialApi.getMaterialPreviewUrl(filename),
      path: filePath,
      size: file.size,
      type: file.type
    }
    ElMessage.success('封面图片上传成功')
  } else {
    ElMessage.error(response.msg || '封面图片上传失败')
  }
}

const handleCoverUploadError = () => {
  ElMessage.error('封面图片上传失败')
}

const changeCoverImage = () => {
  const uploadElement = document.querySelector('.cover-uploader input[type="file"]')
  if (uploadElement) uploadElement.click()
}

const removeCoverImage = () => {
  coverImage.value = null
  ElMessage.success('封面图片已删除')
}

// 话题相关
const addCustomTopic = () => {
  if (!customTopic.value.trim()) {
    ElMessage.warning('请输入话题内容')
    return
  }
  if (!selectedTopics.value.includes(customTopic.value.trim())) {
    selectedTopics.value.push(customTopic.value.trim())
    customTopic.value = ''
    ElMessage.success('话题添加成功')
  } else {
    ElMessage.warning('话题已存在')
  }
}

const toggleRecommendedTopic = (topic) => {
  const index = selectedTopics.value.indexOf(topic)
  if (index > -1) {
    selectedTopics.value.splice(index, 1)
  } else {
    selectedTopics.value.push(topic)
  }
}

const removeTopic = (index) => {
  selectedTopics.value.splice(index, 1)
}

// 重置表单
const resetForm = () => {
  selectedPlatforms.value = []
  Object.keys(selectedAccounts).forEach(key => {
    selectedAccounts[key] = []
  })
  fileList.value = []
  coverImage.value = null
  title.value = ''
  description.value = ''
  selectedTopics.value = []
  scheduleEnabled.value = false
  videosPerDay.value = 1
  dailyTimes.value = ['10:00']
  startDays.value = 0
  isOriginal.value = false
  ElMessage.success('表单已重置')
}

// 发布逻辑
const handlePublish = async () => {
  if (publishing.value || !canPublish.value) return
  
  publishing.value = true
  publishProgress.value = 0
  publishResults.value = []
  progressDialogVisible.value = true
  
  const tasks = []
  selectedPlatforms.value.forEach(platformKey => {
    const accounts = selectedAccounts[platformKey] || []
    accounts.forEach(accountId => {
      const account = accountStore.accounts.find(acc => acc.id === accountId)
      if (account) {
        tasks.push({
          platformKey,
          platformName: getPlatformName(platformKey),
          accountId,
          accountName: account.name,
          accountFilePath: account.filePath
        })
      }
    })
  })
  
  for (let i = 0; i < tasks.length; i++) {
    const task = tasks[i]
    
    publishResults.value.push({
      platform: task.platformName,
      account: task.accountName,
      status: 'pending',
      message: '发布中...'
    })
    
    const publishData = {
      type: task.platformKey,
      title: title.value,
      description: description.value,
      tags: selectedTopics.value,
      fileList: fileList.value.map(f => f.path),
      accountList: [task.accountFilePath],
      enableTimer: scheduleEnabled.value ? 1 : 0,
      videosPerDay: scheduleEnabled.value ? videosPerDay.value : 1,
      dailyTimes: scheduleEnabled.value ? dailyTimes.value : ['10:00'],
      startDays: scheduleEnabled.value ? startDays.value : 0,
      category: isOriginal.value ? 1 : 0,
      productLink: '',
      productTitle: '',
      isDraft: false,
      thumbnail: coverImage.value ? coverImage.value.path : ''
    }
    
    try {
      await http.post('/postVideo', publishData)
      publishResults.value[i].status = 'success'
      publishResults.value[i].message = '发布成功'
    } catch (error) {
      publishResults.value[i].status = 'error'
      publishResults.value[i].message = error.message || '发布失败'
    }
    
    publishProgress.value = Math.floor(((i + 1) / tasks.length) * 100)
  }
  
  publishing.value = false
  
  const successCount = publishResults.value.filter(r => r.status === 'success').length
  const failCount = publishResults.value.filter(r => r.status === 'error').length
  
  if (failCount === 0) {
    ElMessage.success(`全部发布成功，共 ${successCount} 个账号`)
  } else {
    ElMessage.warning(`发布完成：成功 ${successCount} 个，失败 ${failCount} 个`)
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.one-click-publish {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  
  .page-header {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid #ebeef5;
    
    h2 {
      font-size: 24px;
      color: $text-primary;
      margin: 0 0 8px 0;
    }
    
    .subtitle {
      font-size: 14px;
      color: $text-secondary;
      margin: 0;
    }
  }
  
  .section {
    margin-bottom: 30px;
    
    h3 {
      font-size: 16px;
      color: $text-primary;
      margin: 0 0 15px 0;
      
      .required {
        color: #F56C6C;
      }
      
      .optional {
        font-size: 12px;
        color: $text-secondary;
        font-weight: normal;
      }
    }
    
    h4 {
      font-size: 14px;
      color: #606266;
      margin: 0 0 10px 0;
    }
  }
  
  .platform-checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
  }
  
  .account-group {
    margin-bottom: 20px;
    padding: 15px;
    background: #f5f7fa;
    border-radius: 4px;
  }
  
  .account-checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
  }
  
  .no-account {
    color: #909399;
    font-size: 13px;
  }
  
  .uploaded-files {
    margin-top: 15px;
    
    .file-item {
      display: flex;
      align-items: center;
      padding: 10px 15px;
      background-color: #f5f7fa;
      border-radius: 4px;
      margin-bottom: 10px;
      
      .el-link {
        margin-right: 10px;
      }
      
      .file-size {
        color: #909399;
        font-size: 13px;
        margin-right: auto;
      }
    }
  }
  
  .upload-options-content {
    display: flex;
    justify-content: center;
    gap: 20px;
    
    .option-btn {
      width: 150px;
      height: 80px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
  }
  
  .video-upload {
    width: 100%;
    
    :deep(.el-upload-dragger) {
      width: 100%;
      height: 180px;
    }
  }
  
  .material-library-content {
    .material-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-height: 400px;
      overflow-y: auto;
      
      .material-item {
        padding: 10px;
        border: 1px solid #ebeef5;
        border-radius: 4px;
        
        .material-info {
          .material-name {
            font-weight: 500;
            margin-bottom: 5px;
          }
          
          .material-details {
            font-size: 12px;
            color: #909399;
            
            span {
              margin-right: 15px;
            }
          }
        }
      }
    }
  }
  
  .cover-uploader {
    .cover-preview {
      position: relative;
      width: 200px;
      height: 200px;
      border: 1px dashed #dcdfe6;
      border-radius: 6px;
      overflow: hidden;
      cursor: pointer;
      
      .cover-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      
      .cover-actions {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(0, 0, 0, 0.6);
        padding: 8px;
        display: flex;
        justify-content: center;
        gap: 8px;
        opacity: 0;
        transition: opacity 0.3s;
      }
      
      &:hover .cover-actions {
        opacity: 1;
      }
    }
    
    .el-button {
      width: 200px;
      height: 200px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border: 1px dashed #dcdfe6;
      border-radius: 6px;
    }
  }
  
  .title-input,
  .description-input {
    max-width: 600px;
  }
  
  .topic-display {
    display: flex;
    flex-direction: column;
    gap: 12px;
    
    .selected-topics {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      min-height: 32px;
    }
  }
  
  .topic-dialog-content {
    .custom-topic-input {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
      
      .custom-input {
        flex: 1;
      }
    }
    
    .recommended-topics {
      h4 {
        margin: 0 0 16px 0;
        font-size: 16px;
        font-weight: 500;
        color: #303133;
      }
      
      .topic-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 12px;
        
        .topic-btn {
          height: 36px;
          font-size: 14px;
          border-radius: 6px;
        }
      }
    }
  }
  
  .schedule-controls {
    display: flex;
    flex-direction: column;
    gap: 15px;
    
    .schedule-settings {
      margin-top: 15px;
      padding: 15px;
      background-color: #f5f7fa;
      border-radius: 4px;
      
      .schedule-item {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        flex-wrap: wrap;
        gap: 10px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .label {
          min-width: 120px;
        }
        
        .el-time-select {
          margin-right: 10px;
        }
      }
    }
  }
  
  .action-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 15px;
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
  }
  
  .publish-progress {
    padding: 20px;
    
    .publish-results {
      margin-top: 20px;
      border-top: 1px solid #EBEEF5;
      padding-top: 15px;
      max-height: 300px;
      overflow-y: auto;
      
      .result-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: #606266;
        
        .el-icon {
          margin-right: 8px;
        }
        
        .platform-account {
          margin-right: 10px;
          font-weight: 500;
        }
        
        .message {
          color: #909399;
        }
        
        &.success {
          color: #67C23A;
        }
        
        &.error {
          color: #F56C6C;
        }
        
        &.pending {
          color: #909399;
        }
      }
    }
  }
}
</style>
