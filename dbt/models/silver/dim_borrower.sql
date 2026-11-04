select b.borrower_id, b.zip, z.city, z.county_label, z.focus, b.score0 as score_at_origination, b.ltv, b.dti, b.balance
from {{ source('ref', 'borrowers') }} b
left join {{ source('ref', 'zip_areas') }} z using (zip)
