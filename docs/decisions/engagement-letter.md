# Decision (attorney): the engagement letter and fee agreement

The app shows the client this letter before payment (T6-01, being built now). Below is my **draft**. It is used only after
you approve it in the app; that approval is recorded with your name, the time and the version.

**How to answer:** merge this PR to accept the three recommendations. Write any change to the wording as a PR comment.

---

**1. The wording (Spanish and English, below).** It follows Business and Professions Code § 6148(a), which I read on
leginfo. A fee agreement over $1,000 must be in writing and must state the basis of the fee (here a flat fee), the general
nature of the services, and the responsibilities of the attorney and the client. The included and excluded services come
from `docs/scope-and-review-standards.md`.

*Recommend:* approve as written, after filling in the State Bar number, the costs line, the refund policy and the data
promise. Those four are firm settings, and the letter cannot be shown while one is missing.

- [ ] As recommended
- [ ] Other:

---

**2. Payment waits for your countersignature.** § 6148(a) says the client receives a copy signed by both the attorney and the
client. So the client signs, you countersign with one click on the dashboard, and then the client can pay. The client's PDF
shows both signatures and the SHA-256 of the exact text.

*Recommend:* yes. The cost is a short wait between the client's signature and payment; staff are alerted when a letter
is waiting for you.

- [ ] As recommended
- [ ] Other:

---

**3. Which language governs.** The client reads and signs the letter in her language. Both versions are stored.

*Recommend:* the version the client signed governs, and you approve both languages as equivalent.

- [ ] As recommended
- [ ] Other:

---

## Draft, Spanish

# Acuerdo de servicios legales y honorarios

**BORRADOR para aprobación del abogado. No se usa con clientes hasta que el abogado lo apruebe en la aplicación.**

Este acuerdo es entre **Carbon Law Group** (el abogado **Pankaj Raval**, State Bar of California n.º {bar_number}), "la oficina", y **{client_name}**, "usted". Fecha: {date}.

## 1. Lo que la oficina hará por usted
La oficina preparará estos documentos de planificación patrimonial bajo la ley de California:

{documents}

Esto incluye: revisar sus datos y la revisión de conflictos de intereses; la revisión del alcance por el abogado; la preparación de los documentos; la revisión personal del abogado antes de que usted los vea; una ronda de cambios dentro de este alcance; la preparación y la cita de firma con los testigos o el notario que cada documento necesita; y, si prepara un fideicomiso, la lista para pasar sus bienes al fideicomiso.

## 2. Lo que no está incluido
A menos que lo agreguemos por escrito: la administración de una sucesión (probate); la administración de un fideicomiso después de un fallecimiento; planificación de impuestos más allá de las cláusulas comunes; la sucesión de un negocio; bienes en otros países; fideicomisos para necesidades especiales; la revisión de títulos de propiedad; y cambios legales después de firmar.

## 3. Honorarios
Un honorario fijo por los documentos de la sección 1:

{fee_lines}

**Total: {total}.** Ya incluye los descuentos que usted ganó en la aplicación. {costs_line}

## 4. Pago
Usted paga el total en la aplicación, por medio de Stripe, después de que ambos firmemos este acuerdo. La oficina empieza a preparar sus documentos cuando recibe el pago. {refund_policy}

## 5. Lo que hará la oficina
- Preparar sus documentos con cuidado y revisarlos personalmente antes de que usted los vea.
- Explicarle sus documentos en palabras sencillas y contestar sus preguntas.
- Mantener su información confidencial.

## 6. Lo que hará usted
- Dar información completa y verdadera, y avisarnos si algo cambia.
- Revisar sus documentos y contestar a tiempo.
- Asistir a su cita de firma con una identificación.
- Si prepara un fideicomiso: pasar sus bienes al fideicomiso siguiendo la lista que le daremos.

## 7. Las herramientas de inteligencia artificial
Los personajes de la aplicación son un programa de inteligencia artificial que le enseña y reúne sus datos. No son el abogado ni una persona. El abogado Raval revisa y decide todo. {data_promise}

## 8. Terminar este acuerdo
Usted puede terminar este acuerdo cuando quiera, avisando por escrito a la oficina.

## 9. Su copia
Usted recibe una copia de este acuerdo firmada por usted y por el abogado.

**Firma de usted:** {client_signature}

**Firma del abogado:** {attorney_signature}


## Draft, English

# Legal services and fee agreement

**DRAFT for the attorney's approval. Not used with clients until the attorney approves it in the app.**

This agreement is between **Carbon Law Group** (attorney **Pankaj Raval**, State Bar of California no. {bar_number}), "the office", and **{client_name}**, "you". Date: {date}.

## 1. What the office will do for you
The office will prepare these California estate planning documents:

{documents}

This includes: reviewing your information and the conflict-of-interest check; the attorney's scope review; preparing the documents; the attorney's personal review before you see them; one round of changes within this scope; preparing for and holding the signing appointment with the witnesses or notary each document needs; and, if you are preparing a trust, the checklist for moving your property into the trust.

## 2. What is not included
Unless we add it in writing: probate administration; trust administration after a death; tax planning beyond standard provisions; business succession; property in other countries; special-needs trusts; real property title review; and legal changes after signing.

## 3. Fees
A flat fee for the documents in section 1:

{fee_lines}

**Total: {total}.** It already includes the discounts you earned in the app. {costs_line}

## 4. Payment
You pay the total in the app, through Stripe, after we have both signed this agreement. The office starts preparing your documents when it receives payment. {refund_policy}

## 5. What the office will do
- Prepare your documents carefully and review them personally before you see them.
- Explain your documents in plain words and answer your questions.
- Keep your information confidential.

## 6. What you will do
- Give complete and true information, and tell us if anything changes.
- Review your documents and answer on time.
- Come to your signing appointment with an ID.
- If you are preparing a trust: move your property into the trust using the checklist we give you.

## 7. Artificial intelligence tools
The app's characters are an artificial intelligence program that teaches you and gathers your information. They are not the attorney and not a person. Attorney Raval reviews and decides everything. {data_promise}

## 8. Ending this agreement
You may end this agreement at any time by telling the office in writing.

## 9. Your copy
You receive a copy of this agreement signed by you and by the attorney.

**Your signature:** {client_signature}

**Attorney's signature:** {attorney_signature}

