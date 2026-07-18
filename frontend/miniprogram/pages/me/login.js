const api = require('../../utils/api')

Page({
  onLogin() {
    wx.login({
      success: (res) => {
        api.login(res.code).then(() => {
          wx.showToast({ title: '登录成功' })
          wx.switchTab({ url: '/pages/calendar/calendar' })
        })
      }
    })
  }
})
