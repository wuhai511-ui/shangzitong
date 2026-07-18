const api = require('../../utils/api')

Page({
  data: { result: null },
  submit(e) {
    const form = e.detail.value
    wx.showLoading({ title: '分析中...' })
    wx.request({
      url: getApp().globalData.baseUrl + '/api/v1/recommend',
      method: 'POST',
      header: { 'Authorization': `Bearer ${getApp().globalData.token}`, 'Content-Type': 'application/json' },
      data: { purchase_date: form.date, amount: parseFloat(form.amount) },
      success: (res) => {
        wx.hideLoading()
        this.setData({ result: res.data })
      },
      fail: () => { wx.hideLoading(); wx.showToast({ title: '分析失败', icon: 'none' }) }
    })
  }
})
