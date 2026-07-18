const api = require('../../utils/api')

Page({
  data: { cards: [] },
  onShow() { this.loadCards() },
  loadCards() {
    api.getCards().then(cards => this.setData({ cards }))
  },
  addCard() {
    wx.navigateTo({ url: '/pages/cards/add/add' })
  },
  deleteCard(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '删除后数据不可恢复',
      success: (res) => {
        if (res.confirm) {
          api.deleteCard(id).then(() => this.loadCards())
        }
      }
    })
  }
})
