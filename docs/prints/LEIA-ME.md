# Lista de prints a incluir nesta pasta

Salve as capturas de tela com exatamente estes nomes. O README.md já aponta para eles.

| Arquivo | O que capturar | Onde |
|---|---|---|
| `01-fluxo-completo.png` | Os 8 nodes conectados, com o zoom ajustado (tecla `1`) | Editor do n8n |
| `02-execucao-sucesso.png` | Execução concluída com os nodes em verde, ou a aba Executions com *Success* | n8n |
| `03-node-webhook.png` | Node Webhook aberto (duplo clique) mostrando método e path | n8n |
| `04-node-http-request.png` | Node HTTP Request aberto. **Esconda o valor do token** | n8n |
| `05-node-switch.png` | Node Switch com as regras de categoria | n8n |
| `06-node-set-reclamacao.png` | Node Set de reclamação | n8n |
| `07-node-set-solicitacao.png` | Node Set de solicitação | n8n |
| `08-node-set-duvida.png` | Node Set de dúvida | n8n |
| `09-node-set-outro.png` | Node Set de outro | n8n |
| `10-node-responder-webhook.png` | Node Respond to Webhook | n8n |
| `11-saida-webhook.png` | Aba Output do Webhook, após uma execução | n8n |
| `12-saida-http-request.png` | Aba Output do HTTP Request (JSON da IA) | n8n |
| `13-saida-switch.png` | Aba Output do Switch (ramificação usada) | n8n |
| `14-saida-set.png` | Aba Output do node Set usado | n8n |
| `15-resposta-final.png` | Resposta final recebida no curl/Postman | Terminal ou Postman |
| `16-interface-web.png` | Página inicial com um resultado | `/` da API |
| `17-swagger.png` | Documentação interativa | `/docs` da API |

## Cuidados
- Não deixe aparecer o `API_TOKEN`, a `LLM_API_KEY` nem a URL do webhook de produção com credenciais.
- Para ver a saída de cada node, execute o fluxo e dê duplo clique no node, na aba **Output**.
