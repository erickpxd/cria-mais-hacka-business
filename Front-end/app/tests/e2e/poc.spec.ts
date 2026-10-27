import { expect, test } from '@playwright/test'

test('login demo envia uma arte e apresenta desvios para revisão', async ({ page }) => {
  test.setTimeout(90_000)
  await page.goto('/login')
  await page.evaluate(() => localStorage.clear())
  await page.reload()

  await page.getByRole('button', { name: 'Entrar na demonstração' }).click()
  await expect(page.getByRole('heading', { name: /Vamos colocar as campanhas/ })).toBeVisible()
  await page.getByRole('link', { name: '+ Novo projeto' }).click()

  const projectName = 'Campanha Automatizada de Cuidados Diários'
  await page.getByLabel('Nome do projeto *').fill(projectName)
  await page.getByLabel('Objetivo *').fill('Validar a conformidade de uma arte pronta')
  await page.getByLabel('Produto *').fill('Shampoo 400 ml')
  await page.getByLabel('Preço informado').fill('17,90')
  await page.getByLabel('Informação obrigatória').fill('Oferta válida enquanto durarem os estoques.')
  await page.getByRole('button', { name: 'Criar projeto' }).click()

  await expect(page).toHaveURL(/\/projetos\/\d+$/)
  await expect(page.getByRole('heading', { name: projectName })).toBeVisible()
  await page.getByLabel('+ Enviar arte para validar').setInputFiles('src/assets/cria-mais-logo.png')
  await expect(page.locator('.art-card')).toHaveCount(1, { timeout: 20_000 })

  await page.locator('.art-card a').first().click()
  await expect(page.getByRole('heading', { name: /Encontramos \d+ pontos? para revisar/ })).toBeVisible({
    timeout: 70_000,
  })
  await expect(page.locator('.finding-card').first()).toBeVisible()
  await expect(page.getByText(/Logo Pague Menos|institucional|Informação obrigatória/).first()).toBeVisible()
})
