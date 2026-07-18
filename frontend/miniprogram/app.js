App({
  globalData: {
    baseUrl: 'https://api.szt.example.com',
    token: null
  },
  onLaunch() {
    const token = wx.getStorageSync('token')
    if (token) this.globalData.token = token
  }
})
