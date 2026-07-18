const app = getApp()

Page({
  data: { userInfo: {} },
  onShow() {
    if (!app.globalData.token) {
      wx.navigateTo({ url: '/pages/me/login' })
    }
  },
  goToCards() { wx.switchTab({ url: '/pages/cards/cards' }) },
  goToUpload() { wx.switchTab({ url: '/pages/upload/upload' }) },
  goToPurchase() { wx.navigateTo({ url: '/pages/purchase/purchase' }) },
  logout() {
    wx.showModal({
      title: '确认退出',
      success: (res) => {
        if (res.confirm) {
          app.globalData.token = null
          wx.removeStorageSync('token')
          wx.navigateTo({ url: '/pages/me/login' })
        }
      }
    })
  }
})
