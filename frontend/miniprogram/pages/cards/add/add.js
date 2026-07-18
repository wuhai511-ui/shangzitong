const api = require('../../utils/api')

Page({
  data: { banks: ['招商银行','工商银行','建设银行','农业银行','中国银行','交通银行','浦发银行','中信银行','光大银行','民生银行','平安银行','兴业银行'] },
  onBankSelect(e) { this.setData({ bankIndex: e.detail.value }) },
  submit(e) {
    const form = e.detail.value
    api.createCard({
      bank_name: this.data.banks[this.data.bankIndex || 0],
      card_tail: form.card_tail,
      credit_limit: parseFloat(form.credit_limit),
      used_limit: parseFloat(form.used_limit) || 0,
      bill_day: parseInt(form.bill_day),
      due_day: parseInt(form.due_day)
    }).then(() => {
      wx.showToast({ title: '添加成功' })
      wx.navigateBack()
    }).catch(() => wx.showToast({ title: '添加失败', icon: 'none' }))
  }
})
