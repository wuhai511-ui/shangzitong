const app = getApp()

Page({
  data: { report: {}, dimensions: [] },
  onShow() {
    wx.request({
      url: app.globalData.baseUrl + '/api/v1/report/monthly',
      header: { 'Authorization': `Bearer ${app.globalData.token}` },
      success: (res) => {
        const r = res.data
        this.setData({
          report: r,
          dimensions: [
            { name: '免息期利用率', score: Math.round((r.dimensions?.free_days_util || 0) * 100) },
            { name: '还款准时率', score: Math.round((1 - (r.dimensions?.overdue_rate || 0)) * 100) },
            { name: '资金稳定性', score: Math.round((1 - (r.dimensions?.gap_frequency || 0)) * 100) },
            { name: '额度健康度', score: Math.round((1 - (r.dimensions?.card_utilization || 0)) * 100) },
          ]
        })
      }
    })
  }
})
