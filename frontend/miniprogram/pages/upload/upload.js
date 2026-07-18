const api = require('../../utils/api')

Page({
  data: { preview: null, importing: false },
  chooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success: (res) => {
        const file = res.tempFiles[0]
        wx.showLoading({ title: '解析中...' })
        api.uploadPreview(file.path).then(data => {
          wx.hideLoading()
          this.setData({ preview: data, mappings: data.mappings })
        }).catch(() => { wx.hideLoading(); wx.showToast({ title: '解析失败', icon: 'none' }) })
      }
    })
  },
  confirm() {
    this.setData({ importing: true })
    api.confirmImport(this.data.mappings, 'other').then(data => {
      wx.showToast({ title: `导入${data.imported}条` })
      this.setData({ preview: null, importing: false })
    }).catch(() => { wx.showToast({ title: '导入失败', icon: 'none' }); this.setData({ importing: false }) })
  }
})
