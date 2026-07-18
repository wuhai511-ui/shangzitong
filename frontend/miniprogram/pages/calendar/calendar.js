const api = require('../../utils/api')

Page({
  data: {
    calendar: [],
    totalInflow: 0,
    totalOutflow: 0,
    cashPool: 0
  },

  onShow() {
    if (!getApp().globalData.token) {
      this.login()
    } else {
      this.loadCalendar()
    }
  },

  login() {
    wx.login({
      success: (res) => {
        api.login(res.code).then(() => this.loadCalendar())
      }
    })
  },

  loadCalendar() {
    api.getCalendar().then(data => {
      const cal = data.calendar || []
      let inflow = 0, outflow = 0, pool = 0
      cal.forEach(day => {
        day.dateStr = day.date.slice(5)
        const s = parseFloat(day.settlement || 0)
        pool += s
        inflow += s
        day.repayments = day.repayments || []
        day.repayments.forEach(r => {
          const a = parseFloat(r.amount || 0)
          pool -= a
          outflow += a
        })
        day.settlement = s > 0 ? s.toFixed(0) : null
        day.hasAlert = day.alerts && day.alerts.length > 0
      })
      this.setData({ calendar: cal, totalInflow: inflow.toFixed(0), totalOutflow: outflow.toFixed(0), cashPool: pool.toFixed(0) })
    })
  }
})
