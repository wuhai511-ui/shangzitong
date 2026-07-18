const app = getApp()

function request(method, path, data, auth = true) {
  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    if (auth && app.globalData.token) {
      header['Authorization'] = `Bearer ${app.globalData.token}`
    }

    wx.request({
      url: app.globalData.baseUrl + path,
      method,
      header,
      data,
      success(res) {
        if (res.statusCode === 200) resolve(res.data)
        else if (res.statusCode === 401) {
          app.globalData.token = null
          wx.removeStorageSync('token')
          wx.navigateTo({ url: '/pages/login/login' })
          reject(res)
        } else reject(res)
      },
      fail: reject
    })
  })
}

module.exports = {
  login(code) {
    return request('POST', '/api/v1/auth/login', { code }, false).then(data => {
      app.globalData.token = data.access_token
      wx.setStorageSync('token', data.access_token)
      return data
    })
  },

  // Cards
  getCards() { return request('GET', '/api/v1/cards') },
  createCard(card) { return request('POST', '/api/v1/cards', card) },
  deleteCard(id) { return request('DELETE', `/api/v1/cards/${id}`) },

  // Calendar
  getCalendar() { return request('GET', '/api/v1/calendar') },

  // Forecast
  getForecast() { return request('GET', '/api/v1/settlements/forecast') },

  // Upload
  uploadPreview(filePath) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: app.globalData.baseUrl + '/api/v1/ingest/upload/preview',
        filePath,
        name: 'file',
        header: { 'Authorization': `Bearer ${app.globalData.token}` },
        success(res) { resolve(JSON.parse(res.data)) },
        fail: reject
      })
    })
  },
  confirmImport(mappings, provider) {
    return request('POST', '/api/v1/ingest/upload/confirm', { mappings, provider })
  },

  // Alerts
  getUpcomingAlerts() { return request('GET', '/api/v1/alerts/upcoming') }
}
